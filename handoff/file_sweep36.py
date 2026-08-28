"""File every finding from the run #36 whole-tree sweep as a work order.

TEN batches, 91 of 114 modules read (the remaining six batches were held back while another
agent still owned their modules, and are noted in the handoff). Nothing here is sampled or
ranked-then-truncated -- Hard Rule 0 applies to this run's own queue.

Findings already ACTED ON during the shift are deliberately NOT re-filed:
  * pipeline.write_record top-level key clobber   -> fixed and closed (8c82f409cf3e)
  * wh40k.py unconditional [wiki] provenance      -> fixed and closed (1770c2b84786)
  * canon_backup members()/manifest verdict       -> fixed the same shift, net updated
  * the ten-module discarded-write-verdict family -> handed to a dedicated agent
Anything below is what survived that and still needs somebody.

Severity follows the sweep's own reading, except where a QUESTION was reported: those are filed
at OWNER, because "this might be deliberate design" is not a defect and must not be handed to a
bot to "fix".
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import workorders  # noqa: E402

F = []


def add(code, where, what, severity="MINOR", handler="RUN", batch="", evidence=None):
    F.append(dict(code=code, where=where, what=what, severity=severity, handler=handler,
                  evidence=evidence or {}, found_by="sweep36-%s" % batch))


# ---------------------------------------------------------------- batch 01, verify_math.py
add("VERIFY_MATH_DUPLICATE_SECTION_TAG", "src/verify_math.py sections 19s",
    "Two unrelated sections both carry the tag 'Section 19s' -- the metrics-timestamp check "
    "and the ~150-line prose-interlock battery. Every citation to 19s is now ambiguous, and "
    "this is the THIRD instance of duplicated section tags found in this file (two more were "
    "renamed to 20v/20w earlier the same shift). Anchors: '# ---- Section 19s: both writers of "
    "the metrics ledger stamp a timestamp' and '# ---- Section 19s: THE PROSE INTERLOCKS'.",
    "MAJOR", batch="batch01")
add("VERIFY_MATH_THRESHOLD_CHECK_DOES_NOT_READ_TUNING",
    "src/verify_math.py MIN_CALLS_TO_JUDGE_RATE check",
    "A check labelled 'the threshold itself is the one tuning.py already settled on' compares "
    "against a HARDCODED LITERAL 20, not against tuning.py -- so the label claims a "
    "cross-module agreement the check does not test, and tuning.py could change without this "
    "going red. The file already diagnoses this exact defect in its own text (order "
    "495390283745) and applied the fix elsewhere but never at this site.",
    "MAJOR", batch="batch01")
add("VERIFY_MATH_LITERAL_TAUTOLOGY_ROW", "src/verify_math.py PROPOSED EDIT row",
    "A literal check(label, True, True) that calls no code, self-labelled a 'documentation-only "
    "row'. An AST scan of all 663 check() calls found this is the only remaining one whose "
    "literal-literal form is not deliberate. It is a check that cannot fail sitting in the "
    "battery that exists to find checks that cannot fail.",
    batch="batch01")
add("VERIFY_MATH_SUBSTRING_PINS_ON_BARE_IDENTIFIERS",
    "src/verify_math.py source-substring checks",
    "Several checks pin on a single generic identifier rather than a code-shaped fragment, e.g. "
    "'\"ALL_JOBS\" in _allsweep_src', which is also matched by a COMMENT at allsweep.py:351. "
    "Currently correct, and defeatable by any comment reproducing the word. Same shape as the "
    "nine drill nets rewritten this shift and the feats.py continuation pin replaced today: "
    "ask the parse tree, not the file text.",
    "MINOR", "OWNER", batch="batch01")

# ---------------------------------------------------------------- batch 03
add("COVERAGE_BEST_TABLE_ASYMMETRIC_DEFAULT_CAP", "src/coverage.py main() --show-best",
    "--show-best defaults to a silent cap of 10 rows on BEST COVERED while its sibling --show "
    "(WORST COVERED) defaults to unlimited. The asymmetry is undisclosed, so the two halves of "
    "one report answer different questions. Partially addressed earlier this shift by adding a "
    "disclosure line; the asymmetric DEFAULT remains.",
    "MINOR", "OWNER", batch="batch03")
add("THREAD_INTEGRITY_DANGLING_CLASS_NEVER_PRINTED", "src/thread_integrity.py main()",
    "DANGLING -- the most severe of the four measurable classes, 'points at nothing' -- is "
    "computed with full per-pair detail in classify() and then NEVER PRINTED by main(), while "
    "its three less-severe siblings are all itemised. main() is the only reporting surface, so "
    "the worst class is the one nobody can see.",
    "MAJOR", batch="batch03")
add("RUNGUARD_CAS_CHECK_THEN_ACT_WINDOW", "src/runguard.py replace_if_unchanged",
    "The compare-and-swap has a narrow inherent window between the digest read and the rename. "
    "Reported as a QUESTION, not a defect: it is likely an accepted trade-off given this "
    "codebase's stated no-lock-file stance, but nothing states that in the function itself, so "
    "the next reader has to re-derive the reasoning. Either write the reasoning down or close "
    "the window.",
    "MINOR", "OWNER", batch="batch03")

# ---------------------------------------------------------------- batch 05
add("WEAVE_INDEX_STOPNAMES_DROPS_REAL_ENTITIES", "src/weave_index.py _STOPNAMES filter",
    "The _STOPNAMES filter drops entries such as 'father', 'god', 'king' ENTIRELY from "
    "ENTITY_INDEX.json, not merely from cross-source candidate matching as the docstring's "
    "rationale implies. Fullmetal Alchemist's character literally named 'Father' would be "
    "invisible to the index. Low blast radius today (both consumers traced) and squarely a "
    "Hard Rule 0 shape: a filter that silently decides certain named entities do not exist.",
    "MAJOR", "OWNER", batch="batch05")
add("WEAVE_INDEX_DESCRIPTION_TRUNCATED_TO_400", "src/weave_index.py index write",
    "The description field is truncated to 400 characters when written to ENTITY_INDEX.json, "
    "silently. Harmless for the one traced consumer; it is stored data rather than a console "
    "preview, so a future consumer inherits a truncation nothing announces.",
    batch="batch05")
add("ROSETTA_NUMBERED_NOTE_TAG", "src/rosetta.py silence.note tag",
    "Still uses a numbered line tag, silence.note('rosetta.py:136'), rather than the "
    "drift-resistant content label the project moved to elsewhere. Accurate today. This is the "
    "exact pattern weave.py documents having been burned by, and five such tags were retagged "
    "this same shift after going stale.",
    batch="batch05")
add("BUILD_TERMINAL_NON_ATOMIC_WRITE", "src/build_terminal.py registry_terminal.html write",
    "output/registry_terminal.html is written with a plain non-atomic open(..., 'w'). No "
    "concurrent reader was found, so this is a latent hazard rather than a live one -- but it "
    "is the only writer in the module not using the project's atomic idiom.",
    batch="batch05")

# ---------------------------------------------------------------- batch 07
add("CASCADE_POOL_PROOF_NOT_BUCKET_ISOLATED", "src/cascade_bridge.py prove()",
    "prove()'s per-bucket health check is NOT isolated, so POOL_PROOF.json can record a DEAD "
    "bucket as 'answers'. Router.candidates() hands a pinned model the rest of the pool as "
    "backup and stream_chat walks the whole candidate list unbounded (no max_attempts), while "
    "_ask_call's pump() silently ignores failover events -- so a different bucket can serve the "
    "call and the proof credits the one that was asked. Corroborated against the live "
    "data/POOL_PROOF.json, which only ever holds four generic verdict strings and never a "
    "bucket-specific reason. This is a check that cannot fail in the module that decides which "
    "providers the library believes are alive.",
    "MAJOR", batch="batch07")
add("CASCADE_DEAD_FOREVER_HTTP_BRANCH_UNREACHABLE", "src/cascade_bridge.py dead_forever()",
    "The HTTP-code exclusion ('401' in v, etc.) appears structurally unreachable given what "
    "prove() actually writes into `verdict`, and it lacks the word-boundary guard the rest of "
    "this file insists on. A permanent-failure classifier that cannot see permanent failures.",
    batch="batch07")
add("LOGNAMES_BYPASSED_BY_FOUR_LITERAL_CALL_SITES", "src/lognames.py PIPELINE / RECATALOGUE",
    "PIPELINE and RECATALOGUE are hardcoded as bare string literals at four write sites "
    "(overnight.py 605, 1024, 1075 and foreman.py 822) instead of LN.PIPELINE / LN.RECATALOGUE "
    "-- which is exactly the drift this module's own docstring says it was built to prevent, "
    "still live for two of its six names. A single-source-of-truth nothing reads is furniture.",
    "MAJOR", batch="batch07")
add("HOSTS_ADD_DOCSTRING_OVERSTATES_RETURN", "src/hosts.py add()",
    "The docstring claims the return value distinguishes a denied write from a duplicate host; "
    "the code returns a plain False for both. No functional impact (the sole caller needs "
    "neither), but the next caller will believe the docstring.",
    batch="batch07")
add("ANNOUNCED_CONSOLE_TRUNCATION_SCOPE_OF_HARD_RULE_0",
    "src/identity.py top[:6] / src/catalog.py missing[:30]",
    "Both cap a CLI summary listing with an announced '+N more', never affecting the underlying "
    "data the pipeline consumes. THIS IS A QUESTION FOR THE OWNER, not a defect: does Hard Rule "
    "0 reach announced console-report truncation, or only pipeline-consumed rosters? The same "
    "question arose independently in three other batches (handbuilt.py cited[:58], "
    "repass_bands.py 8/14, hosts.discover per_source=24), so a ruling would settle several "
    "orders at once and stop them being re-filed every sweep.",
    "MINOR", "OWNER", batch="batch07")

# ---------------------------------------------------------------- batch 09
add("READ_UNREADABLE_HOSTS_EMPTIES_THE_QUEUE", "src/read.py host lookup",
    "An unreadable WIKI_HOSTS.json sets hosts = {}, and the following `if not h: continue` then "
    "skips EVERY record -- silently emptying the entire read queue. The comment directly above "
    "it says this must not be able to discard the pass. Fails OPEN in the module that is the "
    "library's main throughput, and the failure looks exactly like 'there was nothing to read'.",
    "MAJOR", batch="batch09")
add("READ_CACHEKEY_WRITE_PATH_TOCTOU", "src/read.py read_entity / src/cachekey.py write_path",
    "read_entity() computes its write path once via cachekey.write_path() on entry, then writes "
    "to it unconditionally minutes later after mining, with no re-check. Under read.py's "
    "multi-threaded worker pool this is a TOCTOU race, and it is the exact case-collision pair "
    "('Tag Der Toten' / 'Tag der Toten') the code's own comments cite as having really "
    "happened.",
    "MAJOR", batch="batch09")
add("CORPUS_DB_EVIDENCE_TRUNCATED_DEAD_BRANCH", "src/corpus_db.py evidence_truncated",
    "evidence_truncated is set False once and never reassigned, so the WARNING block and the "
    "meta row built around it are now permanently dead -- leftovers from this shift's own "
    "evidence_limit fix. A warning that can never fire is indistinguishable from a warning that "
    "never had cause to.",
    batch="batch09")
add("GPU_LANE_DEPTH_REFCOUNT_UNLOCKED", "src/gpu_lane.py foreground()",
    "The depth-refcount file is a per-process read-modify-write with no lock. Currently "
    "unreachable -- its only caller, generate.py, is confirmed single-threaded by grep -- so "
    "this is latent, and it stops being latent the moment generation is parallelised.",
    batch="batch09")
add("ADDRESS_SPACE_HARDCODED_HASH_OFFSETS", "src/address_space.py assign()",
    "The galaxy/star/planet hash-slice offsets (8, 48, 78) are hardcoded literals rather than "
    "derived from WIDTHS, contrary to the module's own stated philosophy that every field width "
    "is a named constant. Safe today, and it will silently mis-slice if the census grows.",
    batch="batch09")
add("INGEST_DOC_OVERSIZE_CHUNK_NO_RESPLIT", "src/ingest_doc.py mine()",
    "The chunk builder can emit a chunk LARGER than CHUNK when a single page exceeds it, with "
    "no re-split safety net -- unlike read.py's _local_carded, which has one. The consequence "
    "is silent prompt truncation at the model boundary, which reads as the model having nothing "
    "to say about the tail of a long page.",
    "MAJOR", batch="batch09")
add("COMPRESS_STORE_STALE_NOTE_TAG", "src/compress_store.py silence.note tag",
    "silence.note('compress_store.py:14') sits on line 16, and line 14 is the SUCCESS branch, "
    "not the except ImportError handler the tag is meant to record -- so tracing a swallowed "
    "import failure by this tag leads to the wrong statement.",
    batch="batch09")
add("SLUG_TRUNCATION_INCONSISTENT_BETWEEN_MODULES",
    "src/catalogue_aurora.py slug() vs src/ingest_doc.py slug()",
    "catalogue_aurora.slug() truncates at 60 characters while ingest_doc.slug() is uncapped. "
    "Two slug functions that disagree about length will eventually disagree about identity, "
    "which is how cache keys collide.",
    batch="batch09")

# ---------------------------------------------------------------- batch 10
add("HEALTH_FLUSH_ITERATES_LEDGER_WITHOUT_THE_LOCK", "src/health.py flush()",
    "flush() iterates and clears LEDGER/_SAMPLES WITHOUT holding _LOCK while record() mutates "
    "them under that lock from other threads. REPRODUCED: 235 RuntimeError 'dictionary changed "
    "size during iteration' in a six-thread repro. The crash is then swallowed by silence.note's "
    "blanket except, so state/failures.json silently fails to update on affected cycles -- the "
    "failure ledger losing failures, invisibly, in the module whose job is recording them.",
    "MAJOR", batch="batch10")
add("REFERENCE_COMPARE_PRINTS_A_CLAIM_ITS_OWN_ORDER_REFUTES", "src/reference.py --compare",
    "--compare prints a stale claim that per-axis SCORES are not persisted, citing order "
    "b03f2ab9951a -- and assay.py added a 'scores' field under that very order on 2026-08-26. "
    "The diff does not use it, so the tool tells its reader that a comparison it could now make "
    "is impossible.",
    batch="batch10")
add("MODULE_INDEX_NAMES_A_FILE_THAT_DOES_NOT_EXIST", "src/module_index.py GROUPS",
    "GROUPS['The corpus'] lists 'wikipedia_source', which is not a file in this tree (only "
    "wiki_source.py exists, already listed separately). Filtered silently by `if n in mods`, so "
    "it is harmless -- and it is precisely the stale hand-kept name this module's own docstring "
    "warns about.",
    batch="batch10")

# ---------------------------------------------------------------- batch 11
add("LEDGER_GUARD_STALE_CALLSITE_LINE", "src/ledger_guard.py docstring",
    "The docstring says publish.py:622 calls assert_intact(); the real call site is "
    "publish.py:698.",
    batch="batch11")
add("LEDGER_GUARD_LOSS_TOLERANCE_CANNOT_TELL_TYPO_FROM_FALSIFICATION",
    "src/ledger_guard.py check_since_snapshot MAX_LOST_FRACTION",
    "The 5% loss tolerance cannot distinguish an accidental typo-fix in old ledger text from a "
    "deliberate small falsification of it. The number is explicitly a judgement call by the "
    "agent that wrote it today, not a measurement, and it is the one value in a tamper-evident "
    "guard that is set by taste. An owner ruling would make it evidence. (The containment maths "
    "itself was adversarially tested against combined remove+insert edits and found sound.)",
    "MAJOR", "OWNER", batch="batch11")
add("OVERNIGHT_DUPLICATE_START_BANNER", "src/overnight.py start()",
    "start() writes its per-job 'session started' banner via an UNLOCKED precheck before "
    "_guarded_popen's lock-protected spawn guard, so the keeper thread and the main cycle can "
    "log two start banners for one real process start. The double-spawn itself is correctly "
    "prevented -- only the log evidence is wrong, which matters because this log is the forensic "
    "record runs reconstruct incidents from.",
    batch="batch11")
add("ADDRESS_SHORT_INDEX_NAMES_CAN_MATCH_ANYTHING", "src/address.py spine_code_for()",
    "The token-overlap fallback normalises coverage by min(len(target_tokens), "
    "len(name_tokens)), so any of the 125 of 220 short (<=2-token) Acquisitions-Index entries -- "
    "'Alien', 'Doom', 'Dune', 'Halo', 'Diablo', 'DC' -- can score coverage 1.0 against an "
    "unrelated future source sharing that single word, and bypass UNASSIGNED. Latent: all 16 "
    "fallback-only matches on today's roll were verified genuine. Hard Rule 2 says never invent "
    "an address, and this is the path that could.",
    "MAJOR", batch="batch11")
add("COMPLETENESS_CATEGORY_CACHE_FIXED_TMP_NAME",
    "src/completeness.py category_size_probe cache",
    "state/category_sizes.json is written through a fixed _CS_CACHE_P + '.tmp' name with no "
    "pid/thread disambiguation, from up to six ThreadPoolExecutor workers concurrently -- the "
    "two-writers-one-temp-filename shape that has cost this project data twice. Self-healing "
    "(a corrupt cache reads as empty next run), which is why it is MINOR and not MAJOR.",
    batch="batch11")
add("CATALOGUE_CODEX_SECTION_FALLBACK_NOT_MOST_SPECIFIC",
    "src/catalogue_codex.py section matching",
    "The section-matching substring fallback keeps the same non-'most-specific-wins' shape that "
    "address.py was rewritten to fix. Zero live collisions verified today; the shape is the "
    "finding.",
    "MINOR", "OWNER", batch="batch11")

# ---------------------------------------------------------------- batch 12
add("MUTATE_ONLY_MUTATES_THE_FIRST_OCCURRENCE_PER_LINE", "src/mutate.py _mutations()",
    "line.replace(old, new, 1) only ever mutates the FIRST occurrence of a repeated "
    "operator/keyword on a line, so a line containing two `and`s or two `<`s never gets its "
    "second one independently mutated. Reproduced directly. This is a COVERAGE HOLE IN THE "
    "COVERAGE MEASURER: the whole point of mutation testing is to find checks that cannot fail, "
    "and these are mutations that were never attempted -- reported as killed-or-survived "
    "totals that quietly omit them.",
    "MAJOR", batch="batch12")
add("DRILL_REAP_NET_DOES_NOT_TEST_OWNERSHIP",
    "src/drill.py abandoned_sandboxes_are_reaped",
    "The net never writes an _owner.json for either probe directory, so it does not exercise "
    "the M46 ownership guard AT ALL -- the fix's actual claim (a live owner protects a sandbox "
    "at any age) is untested by the battery. A complete net is staged in "
    "handoff/nets/run36_m46_sandbox_ownership.md and was watched go red before staging; it "
    "needs merging into drill.py, which was owned by another agent when this was found.",
    "MAJOR", batch="batch12")
add("MUTATE_CLAIM_RACE_BETWEEN_MKDTEMP_AND_CLAIM", "src/mutate.py sandbox()",
    "A narrow unproven window between tempfile.mkdtemp() returning and _claim_sandbox() writing "
    "_owner.json, during which a concurrent reap with a small older_than would see an unowned "
    "directory. Microseconds wide and only reachable by a deliberately aggressive reaper; "
    "recorded rather than fixed because the fix (create the file inside mkdtemp's own call) is "
    "not available and a lock would be heavier than the risk.",
    batch="batch12")
add("CLEANUP_CEILING_PREFIX_AMBIGUITY", "src/cleanup.py clean_ceiling",
    "The prefix match picks the shortest candidate with no ambiguity check when two entities "
    "share a name stem. Not reproduced against live data; the missing check is the finding.",
    "MINOR", "OWNER", batch="batch12")
add("MANIFEST_BUILDER_SUBSTRING_MATCH_NO_LENGTH_FLOOR", "src/manifest_builder.py load_record",
    "The substring-match branch has no length floor, so a very short source name can match "
    "broadly. Current data does not misfire; the safety is circumstantial rather than "
    "structural.",
    batch="batch12")
add("TEMPUS_MISSING_POSITIVITY_CHECK", "src/tempus.py prescience_horizon_bits",
    "Lacks the positivity check its sibling physics.py applies to the same class of input -- "
    "and physics.py gained a negative-mass guard earlier this same shift for exactly this "
    "reason.",
    batch="batch12")

# ---------------------------------------------------------------- batch 14
add("WORKORDERS_BATTERY_FAULTS_BLIND_TO_ESTATE_FAULTS", "src/workorders.py battery_faults()",
    "battery_faults() never reads allsweep's new estate_faults key, so an ESTATE-tier failure "
    "-- 'MASTER CHARTER MISSING' is the example -- now correctly FAILS THE BATTERY while filing "
    "NO WORK ORDER. The sweep grades it and the queue cannot see it. Half of a fix landed this "
    "shift; this is the other half, and it was flagged cross-module by the agent that made the "
    "first half.",
    "MAJOR", batch="batch14")
add("WORKORDERS_STALE_MIRRORS_ALLSWEEP_COMMENT", "src/workorders.py bad-formula comment",
    "A comment still claims the bad formula 'mirrors allsweep's own bad formula exactly, so the "
    "two cannot drift into disagreeing about what bad means'. They have now drifted -- see the "
    "estate_faults order above. The comment asserts the very property that just failed.",
    batch="batch14")
add("CHAIN_UNMATCHED_ROSTER_TRUNCATED_TO_40", "src/chain.py CHAIN.json unmatched",
    "unmatched.most_common(40) truncates the PERSISTED roster in CHAIN.json with no total "
    "recorded, so a reader cannot tell 40 from 40-of-900. Ranked-then-truncated stored data, "
    "which Hard Rule 0 forbids outright.",
    batch="batch14")
add("CHAIN_STALE_NOTE_TAGS", "src/chain.py silence.note line tags",
    "Four numeric silence.note tags no longer match their own lines -- 'chain.py:91' is on line "
    "169, plus :155, :161 and :252.",
    batch="batch14")
add("ENDPOINT_CACHE_NO_COMPARE_AND_SWAP", "src/endpoint.py _MEM / _load / _save",
    "The ENDPOINTS.json cache is a whole-file read-once-write-back with no compare-and-swap, "
    "despite documented multi-process writers. The register() path was given a CAS earlier this "
    "shift; this module-level cache was not, so the same lost-update remains through a "
    "different door.",
    "MAJOR", batch="batch14")
add("ENDPOINT_DEAD_RETURN_AFTER_RAISE", "src/endpoint.py register()",
    "An unreachable `return d[source]` sits after an unconditional raise RuntimeError.",
    batch="batch14")
add("HOSTCHECK_LAND_FIXED_TMP_NAME", "src/hostcheck.py _land()",
    "_land() writes WIKI_HOSTS.json -- one of the two files this project has confirmed are "
    "NOT reconstructible from anything else on disk -- through a fixed path + '.tmp' name with "
    "no CAS. scout.py's own docstring, written today, names this file as still carrying the "
    "hazard. Two writers collide on the scratch file itself and the loser's partial content can "
    "be renamed over the target.",
    "MAJOR", batch="batch14")
add("HOSTCHECK_NULL_RATE_CACHE_IGNORES_EXCLUDE", "src/hostcheck.py null_rate()",
    "The cache is keyed by host ONLY, so the `exclude` (source) parameter is honoured for the "
    "first caller per host and silently dropped for every caller after it -- two callers asking "
    "different questions get one answer.",
    batch="batch14")
add("WORLDSEED_UNREACHABLE_PRIMITIVE_TIER", "src/worldseed.py size lookup",
    "The 'primitive': 35 entry is unreachable: f['tech'] can never take that value. Confirmed, "
    "and it is a vocabulary entry that silently describes a world class the generator cannot "
    "produce.",
    batch="batch14")
add("TELLS_RULE_OF_THREE_NARROWER_THAN_ITS_LABEL", "src/tells.py rule-of-three pattern",
    "The 'rule of three' regex requires a trailing alike/all/together, so it matches far less "
    "than its name claims. Filed as a QUESTION: whether that narrowness is deliberate is a "
    "style-contract decision, and a prose detector that over-matches is worse than one that "
    "under-matches.",
    "MINOR", "OWNER", batch="batch14")

# ---------------------------------------------------------------- batch 15
add("OVERWATCH_ASKS_FOR_A_CONTEXT_THE_RUNNER_DOES_NOT_HOLD", "src/overwatch.py _ask()",
    "_ask() requests num_ctx 4096/8192 computed per slice instead of config's 12288, "
    "contradicting the one-runner-one-context doctrine gpu_lane.py and local_agent.py enforce. "
    "verify_math's structural check does not catch it because the value arrives as a kwarg "
    "through pipeline.ask() rather than as a literal in a raw request body -- so the check is "
    "shape-blind exactly where the divergence lives. Note run #36 separately measured that a "
    "num_ctx mismatch is NOT what is currently stalling Ollama, so this is a doctrine violation "
    "to tidy, not the cause of the stall.",
    "MAJOR", batch="batch15")
add("LOCAL_AGENT_BUDGET_CHARGED_BEFORE_THE_OUTCOME", "src/local_agent.py blast budget",
    "The blast-radius budget is charged BEFORE the find-string-uniqueness and --no-apply "
    "outcomes are known, contradicting the comment 'a refused path costs no budget' three lines "
    "away. The model is billed for edits that never happened, so a run of refusals exhausts a "
    "budget that was never spent.",
    batch="batch15")
add("LOCAL_AGENT_FAILED_REVERT_ALARM_DROPPED_ON_ONE_EXIT",
    "src/local_agent.py turn-budget-exhausted exit",
    "A failed-revert ALARM is surfaced on the 'no tool calls' exit path and DROPPED on the "
    "'turn budget exhausted' path. The exit code is still correct; the diagnostic saying the "
    "tree may have been left modified is what goes missing, on the path most likely to be taken "
    "by a run that was going badly.",
    batch="batch15")
add("SILENCE_REPLACE_RETRY_NARROWER_THAN_ITS_PROMISE", "src/silence.py replace_retry",
    "replace_retry only retries and records PermissionError; any other OSError -- a cross-device "
    "rename is the realistic one -- propagates uncaught. That is narrower than write_json's "
    "'never raises' promise, in the function every writer in this project routes through.",
    batch="batch15")

for f in F:
    o = workorders.file_order(**f)
    print("%-12s %-8s %s" % (o["id"], o["severity"], o["code"]))
print("\nfiled %d sweep findings" % len(F))
