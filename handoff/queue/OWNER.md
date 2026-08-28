# OWNER rung -- 49 open orders

## 3c7c8a6e9102  [BLOCKING]  RECATALOGUE_NULLS_PIPELINE_SYNTHESIS

- **where**: src/catalogue_web.py:137,271 -> pipeline.write_record_catalogue
- **found_by**: sweep34-batch05 + maintenance-2026-08-25b live measurement
- **seen**: 1

THE PROJECT STANDING CRITICAL BUG, NOW CONFIRMED WITH A MECHANISM AND A CASUALTY LIST, AND IT WAS ACTIVE. A re-catalogue nulls the pipeline-authored synthesis block. catalogue() and catalogue_composite() return "synthesis": None; write_record_catalogue merges only rec["entries"] against disk and then dumps rec whole, so every OTHER top-level key on disk is taken from the caller or lost. It does not heal, because phase_synthesis skips any source already in done_keys. MEASURED: 185 of 216 records still carry a synthesis block; 31 are null, of which 26 were nulled in the last 24 hours and 10 in t

```
{
  "casualties": "handoff/SYNTHESIS_NULLED_2026-08-25.json",
  "nulled_24h": 26,
  "nulled_2h": 10,
  "sibling_order": "7292a1c3d84b (sweep34-batch05, the mechanism)",
  "still_have_synthesis": 185,
  "stopped_pid": 4536,
  "total_records": 216
}
```

## e0cf3f375c56  [BLOCKING]  MACHINE_HAS_EXHAUSTED_ITS_TCP_EPHEMERAL_PORTS

- **where**: machine:tcp-ephemeral-ports
- **found_by**: owner asked for an update 2026-08-27 + direct measurement
- **seen**: 1

THIS IS NOT A PANSCRIPTUM FAULT AND IT IS DEGRADING THE WHOLE MACHINE. Measured 2026-08-27 14:51. Windows dynamic port range is 49152-65535 = 16,384 ports. The machine currently holds 30,374 ESTABLISHED TCP connections plus 15,263 Bound, 46,356 total. pythonw pid 11468 (-m semsearch.cli watch) alone holds 14,737 connections to localhost:11434 -- roughly 90% of the entire ephemeral range -- and the count is climbing monotonically: 9,599 at 00:30, 1,843 at 01:40, 14,737 at 14:51. That is a connection leak, not load. THE READ LOG NAMES THE CONSEQUENCE DIRECTLY: state/read_auto.log carries WinErro

```
{
  "bound": 15263,
  "cloud_fallbacks_benched": [
    "bigmodel",
    "cerebras",
    "github",
    "groq",
    "mistral",
    "nvidia"
  ],
  "dynamic_port_range": "49152-65535 (16,384)",
  "established": 30374,
  "foreign_conns_to_ollama": 14737,
  "foreign_pid": 11468,
  "leak_trend": "9,599 (00:30) -> 1,843 (01:40) -> 14,737 (14:51)",
  "read_cpu_seconds": 581,
  "read_errors": [
    "WinError 10048 address in use",
    "WinError 10055 no buffer space",
    "TimeoutError"
  ],
  "read_progress": "1,830/409,581 chunks; 175/216,546 entities; 238 to GPU, 200 UNANSWERED",
  "total_tcp": 46356
}
```

## f84cb75edcfe  [MAJOR]  MISBOUND_HOST_PRIME

- **where**: data/WIKI_HOSTS.json: 'Prime World Equipment'
- **found_by**: maintenance-2026-08-25b direct curl probe
- **seen**: 1

prime.fandom.com is bound to the source 'Prime World Equipment' but SERVES THE PRIME HYDRATION DRINK WIKI. Measured this shift: siteinfo on prime.fandom.com returns HTTP 301 to prime-hydration-drink.fandom.com, sitename 'Prime Hydration Wiki'. The correct fiction is at primeworld.fandom.com, sitename 'Prime World Wiki' (verified live, HTTP 200). Rebinding is a curatorial call, so it is filed rather than done. NOTE: rebinding alone will not clear the BINDING_SUSPECT signal -- the catalogued entries are item-level ('Argentum', 'Aurum', 'Bath Potion') and primeworld.fandom.com has no article for 

```
{
  "bound": "prime.fandom.com",
  "correct_fiction_host": "primeworld.fandom.com",
  "serves": "Prime Hydration Wiki (301)",
  "titles_on_correct_host": "Argentum/Aurum/Bath Potion all missing"
}
```

## f07b7d538ed1  [MAJOR]  MISBOUND_HOST_STARREALMS

- **where**: data/WIKI_HOSTS.json: 'Star Realms'
- **found_by**: maintenance-2026-08-25b direct curl probe
- **seen**: 1

starrealms.fandom.com is bound to the source 'Star Realms' but SERVES 'The Brain World Wikia' -- measured this shift, siteinfo HTTP 200, sitename 'The Brain World Wikia', base https://starrealms.fandom.com/wiki/The_Brain_World_Wikia. The catalogued titles ('Trade Federation', 'Blob', 'Star Empire', 'Machine Cult') are genuine Star Realms factions, so the ENTRY NAMES are right and the HOST is wrong. No replacement host found: star-realms.fandom.com and starrealmswiki.fandom.com both return no siteinfo. Star Realms may have no fandom wiki at all, in which case the right answer is to unbind the s

```
{
  "bound": "starrealms.fandom.com",
  "candidates_result": "neither exists",
  "candidates_tried": [
    "star-realms.fandom.com",
    "starrealmswiki.fandom.com"
  ],
  "serves": "The Brain World Wikia"
}
```

## 9a44b1535851  [MAJOR]  RECORDS_WRITTEN_OUTSIDE_THE_RECORD_WRITER

- **where**: src/recover_folder_records.py:145-148
- **found_by**: maintenance-2026-08-25b queue agents
- **seen**: 1

recover_folder_records writes data/records/<slug>.json through silence.write_json rather than pipeline.write_record_catalogue, which is the project's only sanctioned record writer and the one that merges rather than replaces. Its own comment says the deviation is 'flagged in NEXT_STEPS'; NEXT_STEPS.md contains no mention of it. The clobber SYMPTOM was blocked this shift (it now re-reads the live record and skips any source already holding entries, fail-closed on unreadable), but the routing is still outside the contract, and the two-writer hazard on data/records is a known standing bug. Which 

```
{
  "contract": "pipeline.write_record / write_record_catalogue only",
  "symptom_blocked_this_shift": "e6b2693c752f"
}
```

## 60dc7c624c06  [MAJOR]  TIERS_DATA_CONTRADICTS_ADDRESS_PROSE

- **where**: data/TIERS.json vs src/address_space.py
- **found_by**: maintenance-2026-08-25b queue agents
- **seen**: 1

address_space.py states the charting is '168 multiverses -> 8 metaverses -> 6 xenoverses -> 1 hyperverse, strictly nested, zero containment violations'. data/TIERS.json holds 4 distinct hyperverse values ranging 2-5, so _tier_counts() derives a hyperverse population of 6 and shelfmark() prints hyperverse indices the prose says cannot exist. Either the dendrogram cut or the claim is wrong, and the answer moves ADDRESS ARITHMETIC -- every shelfmark already published depends on it. Not touched for that reason.

```
{
  "claimed": "1 hyperverse",
  "measured": "4 distinct values 2-5, derived population 6"
}
```

## 9fb8a6b10c1f  [MAJOR]  CASCADE_BRIDGE_HAS_NO_REACHABLE_MODEL

- **where**: src/cascade_bridge.py live call
- **found_by**: maintenance-2026-08-25b
- **seen**: 1

cascade_bridge has NO reachable model left, so allsweep grades it a bad subsystem every run. Measured this shift: every cloud provider in the roster returns HTTP 402 -- GLM 4.7 (Cerebras) needs billing, Codestral (Mistral) needs a subscription, DeepSeek balance is $0.00, Qwen (DeepInfra) needs positive balance, Qwen (HuggingFace) has depleted its monthly included credits -- and all five LOCAL entries 404 because the models are not pulled: qwen3:30b-a3b-instruct-2507-q4_K_M, the unsloth Q3_K_M GGUF of the same, llama3.1:latest, gemma3:12b, qwen2.5:14b. ollama holds exactly ONE model on this mac

```
{
  "local_404": [
    "qwen3:30b-a3b-instruct-2507-q4_K_M",
    "unsloth Qwen3-30B-A3B Q3_K_M",
    "llama3.1:latest",
    "gemma3:12b",
    "qwen2.5:14b"
  ],
  "local_agent_status": "answering normally on qwen3:8b",
  "ollama_actually_holds": [
    "qwen3:8b (5.2GB)"
  ],
  "providers_402": [
    "cerebras/glm-4.7",
    "mistral/codestral",
    "deepseek",
    "deepinfra/qwen",
    "huggingface/qwen"
  ]
}
```

## 66f96febdb3a  [MAJOR]  SWEEP34_FINDING

- **where**: src/descending_ladder.py:1
- **found_by**: sweep34-batch02
- **seen**: 1

descending_ladder.py has no functional consumers anywhere in src/. Excluding the file itself, grep for descending_ladder|DESCENDING|rung_for_length|shrink_report|transgression_bits|rung_table|FOLD_RUNG|FOLD_GLYPH|compton_confinement_energy|density_at_scale|schwarzschild_radius returns only: derivation.py:476 (a SCAN_MODULES list), anchors.py:43 (prose telling a reader to 'Use transgression_bits()', which no code does), and secondopinion.py:23 (a note about a past finding). Nothing imports the module; none of its seven public functions is ever called. The gap the docstring says it fills is ther

```
{
  "batch": 2,
  "proof": "descending_ladder.py:14  Worse, the omission is silently load-bearing. X.2's Reach axis is measured in metres\n                    :15  and its band edges are 'rung-characteristic lengths' -- but there are no\n                    :16  rung-characteristic lengths below 1e7 m, so every sub-planetary Reach is scored\n                    :16  against a floor that does not exist.\n---\nassay.py:74     'M0':  dict(ruin=1e2,   reach=1e0,   celerity=1e0,   sustain=1e0,   continuity=1e2),\nassay.py:75     'M1':  dict(ruin=1e7,   reach=1e2,   ...\n---\nanchors.py:43   'transgression': 'bits of exception length (X.2 S4, Rissanen). Use transgression_bits().'\n--- no import of descending_ladder anywhere in src/"
}
```

## aad11acb1183  [MAJOR]  SWEEP34_FINDING

- **where**: src/dashboard.py:968
- **found_by**: sweep34-batch11
- **seen**: 1

dashboard.py:968 calls escalation.assert_clear in main(), so the ONE instrument built to display a standing halt refuses to start while a halt stands. Verified live against the current DRILL_BREACH: python src/dashboard.py --once raises SystemHalted before argparse. The daemon on 8777 only shows the halt because it predates it; any restart makes the halt invisible in the place designed to shout about it. Decide: exempt the read-only instrument, or accept that a halt is only readable via escalation.py --status.

```
{
  "batch": 11,
  "proof": "968: _ESC.assert_clear(os.path.basename(__file__))  ||  784-786: // THE HALT IS THE HEADLINE. If the library has stopped itself, nothing else on this page matters until a person rules on it, so it is rendered first, loud, and with the reason -- a halt whose cause you have to go and find is a halt that stays up longer than it should.  ||  live: escalation.SystemHalted: THE LIBRARY IS HALTED and dashboard.py may not proceed."
}
```

## b1f561587b19  [MAJOR]  SWEEP34_FINDING

- **where**: src/prose_gate.py:249
- **found_by**: sweep34-batch09
- **seen**: 1

prose_gate.py:246-253 + 259-269 REPORT ONLY, DO NOT ACT WITHOUT THE OWNER. The 'entries the manifest never asked for' penalty never reaches the verdict: section_shortfall appends the extra-entry complaint to `missing` but adds nothing to `required`, and assert_block_complete raises only on frac < 1.0. A well-formed extra entry adds equally to present and required, so frac does not move. Reproduced against the live module: three complete entries against expected_entries=2 gave present 15, required 15, frac 1.0, NO refusal, while missing carried '1 entry the manifest never asked for'. generate.p

```
{
  "batch": 9,
  "proof": "    extra = max(0, len(blocks) - expected_entries)\n    if extra:\n        missing.append(...)   |   assert_block_complete: frac = present / required ; if frac < (1.0 - SECTION_LOSS_FLOOR): raise   |   live run: blocks=3 expected=2 -> present 15 required 15 frac 1.0 ; assert_block_complete DID NOT REFUSE"
}
```

## 642a95fe9f3c  [MAJOR]  SWEEP34_FINDING

- **where**: src/address_space.py:275-276
- **found_by**: sweep34-batch15
- **seen**: 1

address_space.assign()'s fit() maps a None or missing tier to 0 with no marker, so a source the weave never charted is published at H0/X0/Mt.0 -- indistinguishable from a source genuinely charted into hyperverse 0. Measured against the live tree: 109 of 209 TIERS.json rows carry at least one None tier, and 8 of the 30 sources in WORLDSEEDS.json are among them (e.g. Baki: hyperverse None, xenoverse None, metaverse None, multiverse 37). shelfmark()'s docstring names a compensating warning -- "the note in main() says so out loud rather than letting a zero read as a survey" -- but that note (addre

```
{
  "batch": 15,
  "proof": "def fit(v, field):\n    return (0 if v is None else int(v)) % (1 << WIDTHS[field])   ||  main() line 365: if not tiers: print(\"(TIERS.json absent -- every world addressed at tier zero...)\")  -- only for the whole-file case  ||  measured: TIERS.json rows 209, rows with a None tier 109; WORLDSEEDS sources 30, of those with a None tier 8; Baki -> {hyperverse: None, xenoverse: None, metaverse: None, multiverse: 37}  ||  callers: pipeline.py:1645, profile.py:160"
}
```

## 789f99f2a65f  [MAJOR]  SWEEP34_FINDING

- **where**: src/tiers.py:309
- **found_by**: sweep34-batch11
- **seen**: 1

tiers.py:309 prints 'hyperverse: DECLINED for all 209 shelves' in the same main() that assigns a hyperverse index per source (chart(), 260-267), prints a hyperverse NUMBER per sample stack (348), and writes it to data/TIERS.json (354), which holds FOUR distinct non-null hyperverse values. THIS IS tiers.py's SIDE OF THE OPEN address_space QUESTION AND THE ANSWER IS: THE CLAIM IS STALE, NOT THE CUT. The tier was re-implemented as the grounding of a xenoverse (124-137, 150-186); the top docstring and the 309 print were never updated.

```
{
  "batch": 11,
  "detail": "MEASURED on data/TIERS.json (209 sources): hyperverse index counts {None: 53, 4: 146, 5: 6, 2: 2, 3: 2}; hyperverse_type counts {None: 53, 'immanent': 146, 'ungrounded': 6, 'eternal_cycle': 2, 'demiurgic': 2}. There is deliberately no hyperverse entry in CUTS and the dendrogram cut needs no change; what needs a ruling is what tiers.py says in print and in its header about a tier it does in fact assign per source.",
  "proof": "TOP DOCSTRING 38-39: 'and NO cut for the hyperverse ... that tier is declined rather than charted, and declining it is itself the result'  ||  44: '168 multiverses -> 8 metaverses -> 6 xenoverses -> H declined'  ||  87: 'So H stays ?'  ||  BUT 137: '# The hyperverse therefore comes from grounding.py and from nowhere else.'  ||  151: 'THE HYPERVERSE. A grounding is answered per XENOVERSE, not per shelf.'  ||  265-266: out[s]['hyperverse'] = xg[xi]['index'] ; out[s]['hyperverse_type'] = xg[xi]['grounding']  ||  309: print(f'hyperverse: DECLINED for all {len(srcs)} shelves - uncharted by cause, not omission')  ||  348: prints H{c[hyperverse]} > X{c[xenoverse]} > ...  ||  354: silence.write_json(out, charted, indent=2, ensure_ascii=False)"
}
```

## b317ba3a4f36  [MAJOR]  GENRES_JSON_HOLDS_INFLATED_CONFIDENCES

- **where**: data/GENRES.json
- **found_by**: sweep34-batch14 + maintenance-2026-08-25b fix measurement
- **seen**: 1

genre.py's truncated-denominator bug was FIXED in code this shift, but the stored classifications were deliberately NOT re-derived, because doing so moves published numbers and that is a curatorial call. MEASURED over all 210 records, old top-3 denominator vs the corrected full field: 193 of 210 sources change confidence; ZERO change their genre label; and 63 CROSS THE MODULE'S OWN 0.45 mixed-source flag, all of them downward -- the flagged count goes from 43 to 106. Examples: Adventure Time 0.616 -> 0.509, Street Fighter 0.479 -> 0.246, Rick and Morty 0.706 -> 0.393. So 63 sources that should

```
{
  "confidence_changes": 193,
  "flag_crossings": 63,
  "flagged_after": 106,
  "flagged_before": 43,
  "label_changes": 0,
  "records": 210,
  "rederive_command": "src/genre.py --write"
}
```

## 3eff62be6cc3  [MAJOR]  GROUNDINGS_JSON_HOLDS_INFLATED_CONFIDENCES

- **where**: data/GROUNDINGS.json
- **found_by**: sweep34-batch07 + maintenance-2026-08-25b
- **seen**: 1

grounding.py carries the IDENTICAL truncated-denominator defect as genre.py -- confirmed this shift: classify_text(top=3) over 5 GROUNDINGS, confidence = score / sum(truncated ranked), runners_up = ranked[1:]. On disk data/GROUNDINGS.json shows 48 classified sources storing 2 of 4 runners-up and 159 UNGROUNDED rows storing 3 of 5, all with inflated confidence. The CODE fix is in hand this shift; the stored classifications are not being re-derived, for the same reason as GENRES.json: it moves published numbers. Expect the same shape as genre -- labels stable, confidences down, and some number o

```
{
  "classified_sources": 48,
  "sibling": "GENRES_JSON_HOLDS_INFLATED_CONFIDENCES",
  "stored_runners_up": "2 of 4 (classified), 3 of 5 (ungrounded)",
  "ungrounded_rows": 159
}
```

## 7ebac78494e8  [MAJOR]  CLOUD_BUCKETS_UNREACHABLE_DNS

- **where**: machine DNS/resolver, not src/
- **found_by**: maintenance-2026-08-25b cascade_scratch.db measurement
- **seen**: 5

Four cloud buckets -- deepinfra:free, huggingface:free, cerebras:free, chutes:free -- all fail with `transport: curl: (6) Could not resolve host: <host>` (api.deepinfra.com, router.huggingface.co, api.cerebras.ai, llm.chutes.ai). Four providers, four different domains, one symptom: this is a resolver fault on THIS MACHINE, not a provider refusal. bucket_state.updated_at for all four is 1787510151-1787510152 -- the same second -- so they have not been reachable since then and are silently absent from a pool that is the binding constraint. Explicitly NOT benched: cascade_bridge.local_transport()

```
{
  "buckets": [
    "deepinfra:free",
    "huggingface:free",
    "cerebras:free",
    "chutes:free"
  ],
  "deliberately_not_benched": "cascade_bridge.local_transport guards permanent_refusal",
  "error": "transport: curl: (6) Could not resolve host: <host>",
  "hosts": [
    "api.deepinfra.com",
    "router.huggingface.co",
    "api.cerebras.ai",
    "llm.chutes.ai"
  ],
  "stalled_since": "bucket_state.updated_at 1787510151-1787510152, all four same second"
}
```

## 4e7f1e47d0a0  [MAJOR]  KEEPER_REASSERTS_A_JOB_A_RUN_STOPPED

- **where**: src/autostart.py keeper vs a MANAGER-rung stop
- **found_by**: maintenance-2026-08-25b
- **seen**: 1

A MAINTENANCE RUN CANNOT DURABLY STOP A STANDING JOB, and this shift proved it on the worst possible example. At 22:5x this run stopped catalogue_web --recatalogue (pid 4536) at the MANAGER rung because it was nulling synthesis blocks -- 26 sources in 24 hours. At 23:21 the keeper re-asserted it as pid 59700. Nothing in the escalation chain is visible to the keeper: the MANAGER rung records that a subsystem was stopped, and the supervisor whose job is to keep subsystems up never reads it. So the stop lasted 25 minutes and no human was ever in the loop. THE HALT IS THE ONLY THING THAT ACTUALLY 

```
{
  "gap": "25 minutes",
  "reasserted_at": "23:21:37, pid 59700, by autostart keeper",
  "related": [
    "3c7c8a6e9102",
    "5aa48077886d"
  ],
  "stopped_at": "22:5x, pid 4536, MANAGER rung",
  "why_not_stopped_again": "merge fix landed before the restart; being watched live"
}
```

## e9ff72c7eb48  [MAJOR]  PUBLISHED_DECIMALS_REST_ON_EVIDENCE_THE_FIXED_GUARD_REFUSES

- **where**: data/ASSAYS.json vs magnitude.subject_refusal
- **found_by**: sweep34 magnitude fixer + maintenance-2026-08-25b
- **seen**: 1

magnitude.py:335 Guard 3 -- "the entity must be the DOER" -- NEVER READ THE ENTITY. Proved by AST: verify(entity, got, ev) took the argument and referenced it zero times, and both operands it did consult are entity-agnostic. It failed in BOTH directions: a bystander's deed ("Beerus erased the universe") passed clean onto anyone's sheet, while "planets destroyed by Goku" was REFUSED on Goku's own sheet, because the pattern matched regardless of who the agent was. The guard is now fixed and the fix is measured: over 142,695 cached evidence docs and 52,322 offers clearing the earlier guards, refu

```
{
  "assays_touched": "81 of 217",
  "caveat": "some refusals are alias failures, not bystander credits",
  "data_not_rewritten": true,
  "live_offer_refusal": "0.51% -> 14.10%",
  "pct": "12.4%",
  "published_decimals": 885,
  "refused_by_fixed_guard": 110,
  "rescued": 6
}
```

## c614f7c145fc  [MAJOR]  A_HALT_WAS_LIFTED_BY_AN_AUTOMATED_ACTOR

- **where**: state/HALT.json cleared_by=owner-cli at 2026-08-26 00:55:07
- **found_by**: maintenance-2026-08-25b
- **seen**: 1

THE HALT WAS LIFTED AT 00:55 BY SOMETHING AUTOMATED, NOT BY A PERSON, AND YOU SHOULD KNOW THAT BEFORE YOU READ ANYTHING ELSE THIS RUN DID. Raised 22:18 by drill.py (DRILL_BREACH, twin detection). Lifted 00:55:07 recorded as who=owner-cli -- which is the CLI default label, NOT evidence a human ruled. No person was present; this was a scheduled run. Every agent this run dispatched was told in writing: do NOT lift the halt, do NOT raise one. One of them lifted it anyway, by the sanctioned route -- python src/escalation.py --clear --ruling "..." -- which passes the runtime guard precisely because 

```
{
  "agents_were_instructed": "do NOT lift the halt (every agent, in writing)",
  "export_scan_after": "0 blocking hits, 9 suppressed with reasons",
  "lifted": "00:55:07 who=owner-cli",
  "merits": "ruling accurate; cause fixed and independently re-verified; drill 218/218/0; verify_math 805/0",
  "no_new_halt_raised": "the fault is repaired; halting to punish a breach would fabricate one",
  "outward_consequence": "public pushes at 01:01 and 01:07",
  "raised": "22:18:32 drill.py DRILL_BREACH",
  "route": "python src/escalation.py --clear --ruling (passes the runtime guard by design)"
}
```

## 1b7f14efce8e  [MAJOR]  BINDING_HOST_SERVES_ANOTHER_WIKI

- **where**: prime.fandom.com
- **found_by**: binding_health.identity
- **seen**: 7

prime.fandom.com is bound to 'Prime World Equipment' but SERVES 'Prime Hydration Wiki' (name agreement 50.0%). The catalogued entry names may be perfectly good; the host is wrong. Rebinding or unbinding a source is a curatorial call, so it is filed, not done.

```
{
  "detail": "the wiki serves something else entirely",
  "matched": "Prime World Equipment",
  "probe": "sitename 'Prime Hydration Wiki'",
  "score": 50.0,
  "sitename": "Prime Hydration Wiki",
  "sources": [
    "Prime World Equipment"
  ],
  "verdict": "MISBOUND"
}
```

## 2d6bef2aef03  [MAJOR]  BINDING_HOST_SERVES_ANOTHER_WIKI

- **where**: starrealms.fandom.com
- **found_by**: binding_health.identity
- **seen**: 7

starrealms.fandom.com is bound to 'Star Realms' but SERVES 'The Brain World Wikia' (name agreement 36.36363636363637%). The catalogued entry names may be perfectly good; the host is wrong. Rebinding or unbinding a source is a curatorial call, so it is filed, not done.

```
{
  "detail": "the wiki serves something else entirely",
  "matched": "Star Realms",
  "probe": "sitename 'The Brain World Wikia'",
  "score": 36.36363636363637,
  "sitename": "The Brain World Wikia",
  "sources": [
    "Star Realms"
  ],
  "verdict": "MISBOUND"
}
```

## 505177847f43  [MAJOR]  LOCAL_LANE_STARVED_BY_A_FOREIGN_PROCESS

- **where**: localhost:11434
- **found_by**: maintenance-2026-08-26 direct measurement
- **seen**: 1

THE LOCAL RUNG IS EFFECTIVELY CLOSED AND THE CAUSE IS NOT PANSCRIPTUM. Measured 2026-08-26: a non-Panscriptum process -- pythonw.exe pid 11468, command line "-m semsearch.cli watch", started 09:33 -- holds 9,599 ESTABLISHED connections plus 12 SynSent to localhost:11434. Ollama itself is alive (a trivial 8-token chat returns in 2.6s; a 6,000-char prompt returns in 6.2s), and the GPU is at 98% with 9.3 of 10.2 GB resident, qwen3:8b pinned with an effectively infinite keep_alive. But a real local_agent order (retag three stale silence.note line numbers in address_space.py -- a small, well-specif

```
{
  "established_conns_to_ollama": 9599,
  "foreign_cmdline": "pythonw -m semsearch.cli watch",
  "foreign_pid": 11468,
  "gpu": "9286/10240 MiB, 98% util",
  "model": "qwen3:8b, keep_alive effectively infinite",
  "real_order_outcome": "ok=false transport TimeoutError, 0 patches, >15 min",
  "six_kb_prompt_latency_s": 6.2,
  "synsent": 12,
  "thinking_model_empty_content_at_num_predict": 64,
  "trivial_chat_latency_s": 2.6
}
```

## ec67de571754  [MAJOR]  CANONICAL_DATA_FILES_HAVE_NO_BACKUP

- **where**: data/
- **found_by**: maintenance-2026-08-26 (incident during run35 batch L4)
- **seen**: 1

NO BACKUP EXISTS FOR THE CANONICAL DATA FILES, and that was found the expensive way. On 2026-08-26 a maintenance agent verifying a fix to roll.exclude() passed test rows via the rows= parameter specifically to AVOID touching the live roll; the write path ignored rows= and landed on data/SWEEP_ROLL.json anyway, destroying the real 216-source roll TWICE. It was recovered both times only because data/records/*.json is canonical and the roll is derivable from it, plus two dated owner rulings in handoff/AUTONOMOUS_PLAN.md and HANDOFF.md supplied the 8 out-of-scope sources notes. Verified intact by 

```
{
  "ad_hoc_backup_made": "state/backups/SWEEP_ROLL.json.reconstructed-20260826",
  "incident": "roll.exclude(rows=) overwrote data/SWEEP_ROLL.json twice, 2026-08-26",
  "recovered_from": "data/records/*.json + dated owner rulings",
  "trap_fixed": "roll.exclude no longer writes when rows= is supplied; drill net added",
  "unbacked_and_NOT_derivable": [
    "data/WIKI_HOSTS.json",
    "data/CHARTER_SPINE_CODES.json"
  ],
  "verified_intact": "216 roll names == 216 record sources, both directions"
}
```

## ae25c89f0179  [MAJOR]  SWEEP35_FINDING

- **where**: onomast.py:311-334,385
- **found_by**: sweep35-batch05
- **seen**: 1

onomast.register_for()'s documented genre+feature blend (FEATURE_SHIFT/GENRE_WEIGHT/FEATURE_WEIGHT, lines 278-334) is unreachable from the only production call site. name_worlds() calls register_for(v["continuity_group"]) at line 385 -- a SINGLE positional argument -- so genre_register and features both default to None, and register_for()s very first branch (line 318: if not genre_register and not features) fires every time, returning the pure hash-of-group-id fallback. That fallback is the exact behaviour the docstring (lines 314-317) says was already fixed as a defect: "That fallback used to

```
{
  "proof": "onomast.py:385: reg = register_for(v[\"continuity_group\"])  --  onomast.py:318: if not genre_register and not features: return REGISTER_ORDER[hash(...)]  --  RESOLVED_ENTITIES.json sample record has no genre/features key"
}
```

## 3fb312a72435  [MAJOR]  SWEEP35_FINDING

- **where**: hosts.py
- **found_by**: sweep35-batch03
- **seen**: 1

src/hosts.py is a finished, working, self-consistent module (docstring: sources should be read from MORE than one host) with NO caller anywhere in the pipeline. Nothing imports hosts.py (grep for "import hosts" across src/*.py returns zero hits); nothing calls hosts_for() or primary_host() outside hosts.py itself; nothing references data/SOURCE_HOSTS.json outside hosts.py. Yet data/SOURCE_HOSTS.json exists on disk with real content (11,583 bytes, last written 2026-08-22) -- someone ran  and it found real extra hosts -- and that work is inert: feats.py mines only from WIKI_HOSTS.json (feats.py:

```
{
  "proof": "grep -rn \"import hosts\" src/*.py -> only src/hosts.py itself; grep -rn \"hosts_for(\" src/*.py -> only src/hosts.py; grep -rn \"SOURCE_HOSTS\" src/*.py -> only src/hosts.py; feats.py:50 HOSTS = data/WIKI_HOSTS.json (primary only)"
}
```

## 3fb9fc6b9999  [MAJOR]  SWEEP35_FINDING

- **where**: ledger.py
- **found_by**: sweep35-batch03
- **seen**: 1

src/ledger.py (De Pretio, the omniversal currency standard) is fully built and internally tested (verify_math.py lines 266-284 exercise to_standards, from_standards, cross_rate, work_value, assay_to_standards) but has NO caller anywhere in the actual generation pipeline. The only real import of ledger.py in the whole tree is verify_math.py; manifest_builder.py, generate.py, prose_gate.py, and every catalogue_*.py module never import it. The modules own docstring states its purpose is to let entries prose state a price at the Freeport, per the Aperture Doctrine Position Paragraph clause, but gr

```
{
  "proof": "grep for the exact import line \"import ledger as L\" across src/*.py matches only verify_math.py:266; grep for Freeport/STANDARD_GLYPH/Position Paragraph in generate.py and manifest_builder.py: no hits; prompts/*.txt and prompts/*.md carry no currency or glyph reference"
}
```

## a8464e348c5e  [MAJOR]  READ_PASS_STALLED_BY_CONTEXT_MISMATCH_AND_A_FOREIGN_CLIENT

- **where**: localhost:11434
- **found_by**: owner report 2026-08-27 + direct measurement
- **seen**: 1

THE READ PASS IS RUNNING AT AN ETA OF ROUGHLY 1.7 YEARS AND THE CAUSE IS NOT IN THIS LIBRARY. Reported live 2026-08-27: read.py --run had done 1,659 of 326,617 chunks (1%), 175 of 200,169 entities, at 0.01 chunks/s. Measured from here: read.py (pid 31528, started 08:05) has consumed only 239 SECONDS of CPU in that time -- it is waiting, not computing. TWO compounding causes, both external to the code. (1) A CONTEXT MISMATCH: the resident runner serves qwen3:8b at context_length=4096 while config.yaml asks for num_ctx=12288. Ollama holds a model at ONE context size, so every request naming a di

```
{
  "configured_num_ctx": 12288,
  "foreign_cmdline": "pythonw -m semsearch.cli watch",
  "foreign_connections_to_ollama": 1843,
  "foreign_pid": 11468,
  "gpu": "9319/10240 MiB, 98% util",
  "probe": "240s timeout, 240s timeout, then 18.7s success",
  "progress": "1,659/326,617 chunks (1%), 175/200,169 entities, 11,144 feats",
  "rate": "0.01 chunks/s, ETA ~14,572h",
  "read_cpu_seconds": 239,
  "read_pid": 31528,
  "resident_context": 4096
}
```

## 52cd63cee774  [MINOR]  DANDWIKI_QUARANTINE_IS_PERMANENT_BY_DESIGN

- **where**: data/HOST_QUARANTINE.json: www.dandwiki.com
- **found_by**: maintenance-2026-08-25b direct curl probe
- **seen**: 1

www.dandwiki.com's quarantine will never lift on its own and the 24h retry will spend a request a day for ever. Measured this shift: /api.php returns HTTP 403 with the title 'To reduce server load, we had to restrict this action to logged in users only', while https://www.dandwiki.com/wiki/Main_Page returns HTTP 200. So the HOST IS UP and its CONTENT IS REACHABLE -- only the anonymous API is closed, deliberately, by its operators. Four sources are dark behind this: Dr. Firestorm's Engineering Corps, Mage Hand Press, Savant, Yorviing's Arcane Grimoire. Both remedies are owner calls and neither 

```
{
  "api": "HTTP 403 restricted to logged-in users",
  "html": "HTTP 200",
  "sources_dark": [
    "Dr. Firestorm's Engineering Corps",
    "Mage Hand Press",
    "Savant",
    "Yorviing's Arcane Grimoire"
  ]
}
```

## 47c8def059e3  [MINOR]  COSMOLOGY_GRAPH_CONSOLE_TRUNCATES_RANKED_LISTS

- **where**: src/cosmology_graph.py
- **found_by**: maintenance-2026-08-25b queue agents
- **seen**: 1

The console report truncates ranked lists: pair_w[:16], comps[:8], pair_shared[:4], c[:6]. Display-only -- the full data now reaches the JSON after this shift's fix -- but catalogue_models.py:146,158 carries comments recording two of exactly this shape being REMOVED as Hard Rule 0 caps, so the family precedent points the other way. Whether a console summary is a report or a listing is the owner's ruling.

## 85cdecef25f8  [MINOR]  CODEX_WEAPON_PROPERTY_UNMAPPED

- **where**: src/catalogue_codex.py TYPE_CATEGORY
- **found_by**: maintenance-2026-08-25b queue agents
- **seen**: 1

'weapon property' (35 occurrences in the codex) is the third unmapped element type and still defaults to THINGS. Probably POWERS alongside 'rule'/'proficiency' -- the two mapped this shift (ae3bd3847edf) -- but it is a curatorial call.

## 6c479972e838  [MINOR]  LIVENESS_DEAD_NEEDS_RECEIVER_AWARENESS

- **where**: src/liveness.py + drill.LIVENESS_CEILING
- **found_by**: maintenance-2026-08-25b queue agents
- **seen**: 1

liveness's DEAD detection has a real false-negative surface, but the only narrowing that bites is a receiver-aware 'used' set, and that needs a matching LIVENESS_CEILING revision in drill.py in the same commit. The ceiling is a RATCHET -- lowered when code is cleaned up, never raised to go green -- so pairing the two files is an owner-level decision, not a handler's. Note the ceiling currently sits at 38 with ZERO headroom.

## 8c354f6c9780  [MINOR]  AUTOSTART_TWIN_WATCHDOG_FAILS_OPEN_SILENTLY

- **where**: src/autostart.py:121-145,157
- **found_by**: maintenance-2026-08-25b queue agents
- **seen**: 1

_twin_watchdog() returns False ('no twin, proceed') on ANY exception, and runs once before the loop. Both limbs verified. Neither obvious fix is right: failing closed means one transient WMI hiccup at boot leaves the supervisor unwatched until next logon (nothing restarts the .vbs), and re-checking inside the loop creates a mutual-suicide race where two watchdogs see each other and both exit -- the startup-only check avoids that BY DESIGN, since only the newcomer exits. Which failure mode is preferred is the owner's call. A safe middle nobody applied: retry the CIM query a few times before con

## 2b695c192470  [MINOR]  SWEEP34_FINDING

- **where**: sweep.py:68
- **found_by**: sweep34-batch01
- **seen**: 1

CROSS-MODULE (found while auditing verify_math.py). sweep.load (sweep.py:68) has no caller anywhere in src/ -- the only references are verify_math.py's own probes at 3368/3374. Its own docstring at sweep.py:71 asserts 'The only call site (`:129`) asks for the evidence of every Person-category entry ... and does no existence check first', which is not true of sweep.py:129 ('def sweep():') nor of sweep.py:160 (cachekey.load). Curatorial call: delete the function, restore the caller, or record it as a kept public helper -- and fix the docstring either way.

```
{
  "batch": 1,
  "proof": "grep -rn 'sweep\\.load|_sw21\\.load|sw\\.load' src/ -> only verify_math.py:3358, 3368, 3374\nsweep.py:68 def load(path)\nsweep.py:71 'THE ABSENT FILE IS THE NORMAL PATH, NOT A FAILURE. The only call site (`:129`) asks for the'\nsweep.py:160 ev, _ = cachekey.load(F.CACHE, host, e[\"name\"])   <- cachekey.load, not sweep.load"
}
```

## 570525d35825  [MINOR]  SWEEP34_FINDING

- **where**: src/endpoint.py:285-301
- **found_by**: sweep34-batch06
- **seen**: 1

endpoint.py:301 MODE_HTML is defined and referenced nowhere in the tree (grep MODE_HTML across all *.py: one hit, the definition). detect() can only ever return MODE_API, MODE_RAW or MODE_DEAD, so any comparison mode == MODE_HTML is a check that cannot succeed, while the 15-line comment above the constant announces "So a third mode". The HTML capability itself is real but reached another way entirely: feats.py:975-978 uses a "pages:" host prefix through source_pages + fetch_html and never consults detect(). Either delete the constant or make detect() able to return it; a public name deletion i

```
{
  "batch": 6,
  "proof": "301: MODE_HTML = \"html\"  ||  grep -rn MODE_HTML --include=*.py . -> ./src/endpoint.py:301 only  ||  detect() assigns only {\"mode\": MODE_DEAD/MODE_API/MODE_RAW} at 155,161,173"
}
```

## d411f780d347  [MINOR]  SWEEP34_FINDING

- **where**: src/sweep_plan.py:186
- **found_by**: sweep34-batch02
- **seen**: 1

coverage_map() has no callers anywhere in src/. grep returns one hit outside its own definition: line 209, a docstring in covered_by that merely mentions it. Its own docstring calls it 'The authoritative view: shards first, the aggregate file only where a shard is absent' -- yet the CLI path that wants exactly that reads the non-authoritative file directly (main(), lines 314-319, open(COVERAGE)), i.e. --coverage (documented at line 20 as 'what the last sweep actually covered') reports from the convenience view that record()'s own docstring at line 139 says 'nothing draws a conclusion from'. Cu

```
{
  "batch": 2,
  "proof": "186    def coverage_map():\n187        'The authoritative view: shards first, the aggregate file only where a shard is absent.'\n---\n314        elif a.coverage:\n315            try:\n316                with open(COVERAGE, encoding='utf-8') as f:\n317                    data = json.load(f)\n--- grep -rn coverage_map src/ -> sweep_plan.py:186 (def), sweep_plan.py:209 (docstring mention). No callers."
}
```

## 946153deafe9  [MINOR]  SWEEP34_FINDING

- **where**: src/completeness.py:122-129
- **found_by**: sweep34-batch12
- **seen**: 1

completeness.py:122-129 -- category_size() has no caller anywhere in src/ (only mentions are inside category_size_probe's docstring and its silence.note tag; the one importer of the module, verify_math.py, patches category_size_probe and never this). Its docstring's sibling claim at line 92, '`category_size` stays as it was for every caller that only wants the number', names callers that do not exist. Curatorial: delete the function and the sentence, or name the intended caller.

```
{
  "batch": 12,
  "proof": "def category_size(sub, category): ... return category_size_probe(sub, category)[0]  -- grep -rn 'category_size\\b' src/*.py minus category_size_probe returns only this definition"
}
```

## 1770c2b84786  [MINOR]  SWEEP34_FINDING

- **where**: src/wh40k.py:197
- **found_by**: sweep34-batch13
- **seen**: 1

wh40k.py:197 stamps EVERY axis worksheet line '[wiki]' unconditionally, including axes whose evidence contains no quoted material at all (e.g. Nurgle celerity 'The slowest thing in the setting, deliberately. He does not need to arrive'; Khorne volition 'Absolute and unsplittable...'; Khorne discernment 'Sees violence and nothing else...'). Its twin zfighters.py marks provenance per axis and states why in its docstring (lines 14-16), reading the marker off the tuple at line 412. wh40k.py:230-236 already records that a ruling applied to zfighters was not applied to this file; this is a second in

```
{
  "batch": 13,
  "proof": "wh40k.py:197: sheet = {ax: \"[wiki] \" + v[1] for ax, v in rec[\"axes\"].items()}  ||  wh40k.py:63: celerity=(2.0, \"The slowest thing in the setting, deliberately. He does not need to arrive\")  -- no quotation  ||  zfighters.py:14-16: 'Provenance is marked per axis: [wiki] where the sentence is in the mined cache verbatim, [canon] where the event is on-panel at the locus given and the miner did not surface it.'  ||  zfighters.py:412: sheet = {ax: \"[\" + v[2] + \"] \" + v[1] for ax, v in rec[\"axes\"].items()}"
}
```

## 7e360eaec3a6  [MINOR]  SWEEP34_FINDING

- **where**: src/chord_field.py
- **found_by**: sweep34-batch13
- **seen**: 1

chord_field.py is never imported anywhere and none of its public functions has a caller. A repo-wide search for chord_field / total_beta / per_system_beta_without_unification / landauer_floor / recoil_momentum / recoil_velocity / critical_power_self_focus / ADJUDICATIONS finds, outside the file and the handoff archive, exactly one hit: the bare STRING "chord_field" in derivation.py:477's SCAN_MODULES list, which derivation.scan_constants reads off disk with ast.parse and never imports. So the module-level constants ARE reachable but all six functions and ADJUDICATIONS are dead. Already recorde

```
{
  "batch": 13,
  "proof": "derivation.py:477: SCAN_MODULES = [\"assay\", \"feats\", \"cosmography\", \"propagation\", \"descending_ladder\", \"scale_theories\", \"chord_field\", \"resonance\", ...]  ||  derivation.py:481-500 scan_constants(mod) opens HERE/mod + \".py\" and ast.parse()s it -- no import, and it only collects module-level UPPERCASE Assign nodes  ||  grep over src/ for chord_field|total_beta|landauer_floor|recoil_velocity|critical_power_self_focus|ADJUDICATIONS returns only chord_field.py itself and derivation.py:477"
}
```

## de43fe54feb7  [MINOR]  SWEEP34_FINDING

- **where**: src/scope.py:123
- **found_by**: sweep34-batch09
- **seen**: 1

scope.py:123 ceiling_for() has no callers anywhere in the repository -- 'grep -rn ceiling_for src/ docs/ *.md' returns only its own def line (plus prior audit reports). The live path to the same data is magnitude.host_ceiling (magnitude.py:942), which reads SCOPE.json directly and reimplements the live-probe fallback. Reported at handoff/sweep26/AUDIT_batch07.md:250 and in sweeps 23/30/32 and still present; sweep 32's claim that magnitude.py/pipeline.py use it is not borne out by grep. Filed to OWNER because deleting a public function is a curatorial call.

```
{
  "batch": 9,
  "proof": "def ceiling_for(source, hosts=None, cache=None):   |   grep -rn 'ceiling_for' src/ docs/ *.md -> src/scope.py:123 only"
}
```

## 1eb00a84225e  [MINOR]  SWEEP34_FINDING

- **where**: src/address_space.py:133
- **found_by**: sweep34-batch15
- **seen**: 1

address_space.UNADDRESSED is dead: defined at line 133 with a comment describing the honest answer for a shelf that shares no entity with anything, and referenced nowhere in src/. grep -rn UNADDRESSED src/ --include=*.py returns exactly one line, its own definition. Worth keeping only if it is wired into the missing-tier case (the MAJOR order on address_space.py:275); otherwise it is a name for a decision nobody takes.

```
{
  "batch": 15,
  "proof": "UNADDRESSED = None      # a shelf in no hyperverse: it shares no entity with anything   ||  grep -rn \"UNADDRESSED\" src/ --include=*.py  ->  src/address_space.py:133 only"
}
```

## 01695fe3ef26  [MINOR]  SWEEP34_FINDING

- **where**: src/scale_theories.py:23-27,104-148
- **found_by**: sweep34-batch10
- **seen**: 1

scale_theories.py -- nothing in src/ imports this module; its only mention anywhere is its own name inside derivation.SCAN_MODULES. liveness reports all four public functions dead (bulk_export_beta:104, growth_strike:121, penetration_pressure:134, surviving_theory:145) and the five module-level constants at lines 23-27 (C_LIGHT, G_NEWTON, HBAR, NUCLEAR_DENSITY, PLANCK_LENGTH) are read NOWHERE -- not by those functions, not outside the file -- while physics.py:57 owns C and the derivation ledger already carries c, G, hbar, nuclear_density and planck_length as MEASURED roots. So the ledger const

```
{
  "batch": 10,
  "proof": "liveness.py: scale_theories.py:104 bulk_export_beta() / :121 growth_strike() / :134 penetration_pressure() / :145 surviving_theory() -- NEVER RUNS, no caller anywhere in src/. grep scale_theories src/*.py -> only derivation.py:477. grep C_LIGHT|G_NEWTON|HBAR|NUCLEAR_DENSITY|PLANCK_LENGTH src/scale_theories.py -> only the five definition lines 23-27."
}
```

## 665e3609bc82  [MINOR]  SWEEP34_FINDING

- **where**: src/feats.py:542,550,876,1026
- **found_by**: sweep34-batch07
- **seen**: 1

Four functions in feats.py have zero callers anywhere in src/ (verified by grep: the only occurrence of each name is its own def): resolve_title() at 550, _page_exists() at 542, axis_evidence() at 876, remine() at 1026. resolve_title is the consequential one -- its docstring says it exists because catalogue-name/wiki-title mismatch cost 17,148 entries, and evidence_for() calls discover(host, name) with the raw catalogue name instead, so per the call graph that loss is still unmitigated. axis_evidence's three gates were hoisted into by_axis() at 904-910. remine's own comment admits it has no ca

```
{
  "batch": 7,
  "bugs_md": "m80",
  "proof": "grep -rn 'resolve_title|axis_evidence|_page_exists|remine' src/ -> only src/feats.py:542,550,876,1026, all `def` lines"
}
```

## 4e92365b54f6  [MINOR]  SWEEP34_FINDING

- **where**: src/address.py:208
- **found_by**: sweep34-batch07
- **seen**: 1

address.py:208 build_address() has zero callers in src/ (only its own __main__ demo at line 322) AND is stale: it returns f'{spine_code_for(source_name)}/{chapter_slug(...)}', the pre-volume address form. manifest_builder.main() deliberately does not use the bare spine_code_for result -- it builds volume_code[name] first (lines 437-447) because a Series legitimately holds several sources, and its comment records '303 duplicate addresses across 916 of 3,502 jobs' before that fix. Any future caller reaching for the module's named address builder gets the collision the manifest path was repaired 

```
{
  "batch": 7,
  "proof": "grep across src/: build_address appears only at address.py:208 (def) and address.py:322 (its own __main__ print). Body: spine = spine_code_for(source_name); addr = f'{spine}/{volume}'"
}
```

## 0291835411d9  [MINOR]  SWEEP34_FINDING

- **where**: src/tempus.py:67-77
- **found_by**: sweep34-batch15
- **seen**: 1

tempus.DEGENERATE_TIME is dead: a four-entry table at line 67 naming the Basement Loop, the Rot City, the Betweens and the Pale with their charter cross-references, referenced nowhere in src/. loop_report() twenty lines below it re-states the Basement Loop and the Rot City in prose rather than reading them from the table, which is the drift this project keeps finding: one fact, two copies.

```
{
  "batch": 15,
  "proof": "DEGENERATE_TIME = {\n    'the Basement Loop': ('CLOSED', ...), 'the Rot City': ('CLOSED', ...),\n    'the Betweens (deep/Warp)': ('NON-MONOTONIC', ...), 'the Pale': ('UNDEFINED', ...)}\n-- searching src/ for DEGENERATE_TIME returns only this definition; loop_report() at line 112 mentions 'the Basement, the Rot City' in its docstring and reads nothing from the table"
}
```

## 40e98eed6870  [MINOR]  SWEEP34_FINDING

- **where**: src/worldseed.py:184
- **found_by**: sweep34-batch08
- **seen**: 1

Unreachable era/condition vocabulary: worldseed.to_options's size table carries 'primitive' (worldseed.py:184) and burgs.largest_city carries 'primitive' (burgs.py:122), but worldseed.features() can only ever emit one of TECH's four names (spacefaring/industrial/magical/medieval, worldseed.py:95-100) on both the attested and the seeded path. Same for 'settled' in burgs' two condition tables (burgs.py:116,124) against CONDITION's three names (ruined/wartorn/thriving, worldseed.py:90-94). The only producers of era/cond are worldseed features (burgs.main:207, navtree.py:51-53). genre.py:57 does c

```
{
  "batch": 8,
  "proof": "worldseed.py:183 \"size\": {\"spacefaring\":90,\"industrial\":70,\"magical\":55,\"medieval\":45,\"primitive\":35}.get(f[\"tech\"],50) | worldseed.py:95-100 TECH = [(\"spacefaring\",...),(\"industrial\",...),(\"magical\",...),(\"medieval\",...)] | worldseed.py:119 pick = ... % len(table); return table[pick][0], \"seeded\" | burgs.py:122 base = {\"primitive\":2500,...} | grep -rn 'priors' src/ -> only genre.py + unrelated prose"
}
```

## c0384991bfc5  [MINOR]  SWEEP34_FINDING

- **where**: src/worldseed.py:236
- **found_by**: sweep34-batch08
- **seen**: 1

worldseed.unreachable_by_url (worldseed.py:236) has no callers anywhere in src/ -- grep matches only its own definition. Public helper, so this is a deletion decision: keep it with a docstring saying why (as read.cache_path does), or remove it.

```
{
  "batch": 8,
  "proof": "grep -rn 'unreachable_by_url' src/ -> src/worldseed.py:236:def unreachable_by_url(opt): (plus a stale __pycache__ hit only)"
}
```

## f883d9bb534e  [MINOR]  SWEEP34_FINDING

- **where**: src/codewatch.py:109
- **found_by**: sweep34-batch03
- **seen**: 1

codewatch.py:109 twins(): the exclude_pid keyword REPLACES self-exclusion instead of adding to it -- me = os.getpid() if exclude_pid is None else exclude_pid -- so any caller passing exclude_pid would have the calling process itself counted as its own twin, and claim_singleton would stand a daemon down for itself. The parameter has NO caller anywhere in src/ (only twins(needle) and twins(module or who) are used), so it is dead API carrying a trap. Delete the parameter, or make it additive.

```
{
  "batch": 3,
  "proof": "def twins(module, exclude_pid=None):\n    me = os.getpid() if exclude_pid is None else exclude_pid\ncallers: src/codewatch.py:193 twins(module or who); src/drill.py:1999,2004,2094 CW.twins(needle)/CW.twins('anchors')/CW.twins('verify_math') -- none pass exclude_pid"
}
```

## 0fbaba6e1070  [MINOR]  BINDING_RIGHT_ENTRY_NAMES_ARE_NOT_TITLES

- **where**: aneurism.fandom.com
- **found_by**: binding_health.identity
- **seen**: 7

aneurism.fandom.com IS the wiki it is bound to -- it names itself 'ANEURISM Wiki', matching the bound source 'ANEURISM IV' -- but none of its catalogued titles resolve, so the entry names are not article titles there. NOTHING IS BROKEN AND NO BOT CAN FIX IT: the remedy is curatorial, either accept that this source is mined at feature level and carries no per-entry articles, or re-catalogue its entries under names that wiki actually uses. Mining continues either way.

```
{
  "detail": "the wiki names itself after the source bound to it",
  "matched": "ANEURISM IV",
  "probe": "sitename 'ANEURISM Wiki'",
  "score": 100.0,
  "sitename": "ANEURISM Wiki",
  "sources": [
    "ANEURISM IV"
  ],
  "verdict": "CONFIRMED"
}
```

## aecffd7eea57  [MINOR]  BINDING_RIGHT_ENTRY_NAMES_ARE_NOT_TITLES

- **where**: eberron.fandom.com
- **found_by**: binding_health.identity
- **seen**: 7

eberron.fandom.com IS the wiki it is bound to -- it names itself 'Eberron Wiki', matching the bound source 'Eberron: Rising from the Last War' -- but none of its catalogued titles resolve, so the entry names are not article titles there. NOTHING IS BROKEN AND NO BOT CAN FIX IT: the remedy is curatorial, either accept that this source is mined at feature level and carries no per-entry articles, or re-catalogue its entries under names that wiki actually uses. Mining continues either way.

```
{
  "detail": "the wiki names itself after the source bound to it",
  "matched": "Eberron: Rising from the Last War",
  "probe": "sitename 'Eberron Wiki'",
  "score": 100.0,
  "sitename": "Eberron Wiki",
  "sources": [
    "Eberron: Rising from the Last War"
  ],
  "verdict": "CONFIRMED"
}
```

## efd2b537f26d  [MINOR]  BINDING_RIGHT_ENTRY_NAMES_ARE_NOT_TITLES

- **where**: warthunder.fandom.com
- **found_by**: binding_health.identity
- **seen**: 7

warthunder.fandom.com IS the wiki it is bound to -- it names itself 'War Thunder Wiki', matching the bound source 'War Thunder + World of Tanks/Warplanes/Warships (space-refit)' -- but none of its catalogued titles resolve, so the entry names are not article titles there. NOTHING IS BROKEN AND NO BOT CAN FIX IT: the remedy is curatorial, either accept that this source is mined at feature level and carries no per-entry articles, or re-catalogue its entries under names that wiki actually uses. Mining continues either way.

```
{
  "detail": "the wiki names itself after the source bound to it",
  "matched": "War Thunder + World of Tanks/Warplanes/Warships (space-refit)",
  "probe": "sitename 'War Thunder Wiki'",
  "score": 100.0,
  "sitename": "War Thunder Wiki",
  "sources": [
    "War Thunder + World of Tanks/Warplanes/Warships (space-refit)"
  ],
  "verdict": "CONFIRMED"
}
```

