# AUDIT — batch 09, run #48

Modules assigned (read in full, successive chunks, no sampling):

| module | lines read | total lines |
|---|---|---|
| src/foreman.py | 1-1992 | 1992 |
| src/liveness.py | 1-1054 | 1054 |
| src/codewatch.py | 1-953 | 953 |
| src/endpoint.py | 1-577 | 577 |
| src/tiers.py | 1-542 | 542 |
| src/recover_folder_records.py | 1-379 | 379 |
| src/catalogue_models.py | 1-339 | 339 |
| src/tells.py | 1-296 | 296 |

Total: 6,132 lines read, matching `wc -l` for all eight files exactly. foreman.py, liveness.py and
codewatch.py were read directly by this session; endpoint.py, tiers.py and recover_folder_records.py
by one parallel sub-agent and catalogue_models.py/tells.py by a second, both instructed with the
same method and priority list and both required to quote and verify every claim before reporting.

---

## FINDING 1 — MAJOR — nine cross-file line citations in foreman.py have drifted stale; two more in liveness.py

Hard Rule 5 territory, verified individually against the cited file at the cited line. In every
case below the comment's *claim* about what the code does is still true — the corpus is fine —
but the specific `file.py:NNN` pointer a reader is told to open no longer contains that content,
so the citation actively misdirects rather than merely going unhelpfully vague.

**Method**: for each citation, I opened the citing comment in context, then opened the cited
file at the cited line (`awk 'NR==N'` and `sed -n` for a window around it), and separately
`grep`ed the cited file for the actual text/behaviour the comment describes to find where it now
lives.

1. **src/foreman.py:122-123** —
   `# here: verify_math.py:6051 (and again at :6283) records a standing rule that verify_math.py`
   `# and drill.py "are not safe to run" concurrently from an agent context, ...`
   `verify_math.py:6051` is `print("29. §20h A NAMED FAILURE IS NOT AN UNKNOWN ONE, AND A STALE FILE IS NOT AN ALL-CLEAR")` — an unrelated section header. `verify_math.py:6283` is `check("a trailing dot still resolves to the real module so the denylist can see it", ...)` — the NTFS-alternate-data-stream denylist check, also unrelated. The actual "not safe to run concurrently" language (order c349a51ee2c5) lives at **verify_math.py:8592, :9006, :9828 and :10249** today.

2. **src/foreman.py:1426** — the same claim, restated: `` `verify_math.py:5504` records the standing rule that verify_math and drill are not safe to run from an agent context``. Line 5504 is `check("the managed-job roster passes include_self=True", ...)`, part of an unrelated overnight.running() fix. Same real location as #1 above (order c349a51ee2c5, lines 8592/9006/9828/10249).

3. **src/foreman.py:232** — `` `write_json`'s temp carries pid and thread (silence.py:511), which is the collision the helper exists to make unavailable.`` Line 511 of silence.py is mid-comment about where a ledger note is recorded, nothing to do with temp-file naming. The actual `"%s.%d.%d.tmp" % (path, os.getpid(), _th.get_ident())` line inside `write_json` is **silence.py:827**.

4. **src/foreman.py:1774** — the identical claim restated in `owner_queue()`: `` Same `"%s.%d.%d.tmp"` shape as silence.py:511, inline rather than a new helper.`` Same correction: should be **silence.py:827**.

5. **src/foreman.py:294** — `` SAME TEST AS scout.py's OWN found COUNTER (scout.py:616)``. Line 616 of scout.py is a comment about not truncating deferred-source names mid-name. `scout.py`'s actual `found` counter is declared at **scout.py:640** (`results, found = [], 0`).

6. **src/foreman.py:389** — `` health.py:198-210 records the interleaved-writer corruption of `state/failures.json` verbatim``. Lines 198-210 of health.py are the docstring for `FLUSH_CAS_ATTEMPTS`/`_drop_tmp`, unrelated. The interleaved-writer incident this describes ("`failures.json.corrupt` held a valid 102-byte document followed by 38 bytes of a longer, older one") is at **health.py:345-372**.

7. **src/foreman.py:580** — `` The fragment is "read.py --run", which is how overnight.py:1425 actually launches it.`` Line 1425 of overnight.py is inside the unrelated `escalation`-import fail-closed comment in `main()`. The actual STANDING entry that launches `read.py --run` is at **overnight.py:1031** (`("read", [os.path.join(SRC, "read.py"), "--run", "--loop", "5", ...`).

8. **src/foreman.py:638-639** — `` SAME KEY DERIVATION AS standards.py:1511-1512, the code that writes the names this function parses``. standards.py:1511-1512 is prose about the `--recatalogue`/`synthesis`-block blocking order, unrelated. The actual `job = fn[:-4] if fn.endswith(".log") else fn` line that writes the stall-report job names is at **standards.py:1579**.

9. **src/liveness.py:7** — `` `profile.py`'s round trip -- FIXED, now at `profile.py:196-208` ...``. Lines 196-208 of profile.py are mid-function loading `genres.json`/`TIERS.json`, unrelated to the round-trip check. The actual re-encode-and-compare fix (`d = decode(r["profile"])` ... `if d["address"] != r["address"] or re_encoded != r["profile"]:`) is at **profile.py:262-270**.

10. **src/liveness.py:704** — `` cleanup.py:77-80, the founding example in this file's own docstring, is an `if`; nothing made it an `if` except where the author happened to write it.`` This citation asserts that cleanup.py:77-80 currently *is* an `if` statement. It is not: those lines are prose inside `_ruby_question_mark`'s docstring (the measurement paragraph, "Measured after the change: 6,030 ruby sites still stripped..."). This is consistent with liveness.py's own line 10-11 claim that the offending guard "is gone; the function is now a plain scan with no such guard" — so the citation is pointing at wherever cleanup.py happened to land after the fix removed the actual `if`, not at any `if` at all.

11. **INFO, minor** — **src/liveness.py:463** — `` and `coverage._p()`, which has zero callers and is named at liveness.py:10 as the reason this module exists``. `coverage._p()` is actually first named two lines later, at **liveness.py:12**. Trivial drift (off by 2, self-referential within the same docstring), included for completeness rather than as a separate severity-worthy item.

**Why this matters**: several of these citations exist specifically to let a future maintainer *verify* a safety-relevant claim without re-deriving it by hand (the DENYLIST comment at foreman.py:120-125 is a direct example — it tells a reader "don't bother re-adding verify_math/drill to `_checks_pass`, the reason is spelled out at verify_math.py:6051 and :6283"). A reader who follows the pointer today lands on unrelated code, may reasonably conclude the citation was fabricated or the rule no longer holds, and either re-derives the whole argument from scratch or (worse) trusts the wrong nearby text. None of these are line-number citations to LOGIC this batch's files evaluate at runtime, so nothing behaves differently — this is a documentation-integrity finding, not a functional one, but it is exactly the defect class (Hard Rule 5) this sweep is asked to hunt for, and the volume (9 of foreman.py's own 9 cross-file citations, both of liveness.py's non-self-referential citations) suggests the whole citation set in these two files predates a growth spurt in verify_math.py/silence.py/standards.py/health.py/scout.py/overnight.py/profile.py and was never re-verified afterward.

**Proposed remedy**: correct the nine foreman.py citations and two liveness.py citations to the line numbers above (cheap, no behaviour change), and — since this project has already built the "cite by symbol, not by line" convention explicitly for this exact reason (see `verify_math.py`'s own order a09a0e003c31, "CITED BY SYMBOL, NOT BY LINE... the two line numbers[are a] citation with a short shelf life", quoted verbatim in verify_math.py:5507-5510) — consider converting these nine/two citations to name the function/section instead of the line, the same repair verify_math.py already applied to its own citations of `sweep.load`.

---

## FINDING 2 — QUESTION — src/codewatch.py:208-232 and :235-279 (`fingerprint()`, `quiet_seconds()`) — the staleness watch does not descend into `src/deprecated/`, the exact shape of a defect class this codebase has fixed six times elsewhere

`fingerprint()` (line 218: `for name in sorted(os.listdir(root)):`) and `quiet_seconds()` (line 265: `for name in os.listdir(root):`) both enumerate only the top level of `src/`, not subdirectories. `src/deprecated/catalogue_local.py` (280 lines) therefore never contributes to either function's digest or mtime scan, so an edit to it would never make any codewatch-covered daemon consider itself stale.

This is structurally the same shape as `liveness.py:120-129`'s own documented history (`os.listdir(SRC)` "does not descend, and `src/deprecated/` exists and holds `catalogue_local.py`... Third occurrence of the same defect class: `sweep_plan._src_py_files`... and `drill._src_py_files`... were both walked for this same reason and the fix was never propagated here"), and the same class is separately named and fixed in `allsweep.py:289`, `silence.py:264`, and `module_index.py:63`. codewatch.py carries no comment addressing this choice at all, which — in a codebase whose house style is to explain every such decision at length — reads more like an unexamined instance than a considered one.

I am filing this as a QUESTION rather than a finding because I verified the practical consequence is very likely nil today: nothing outside `src/deprecated/` imports `catalogue_local.py` (checked with `grep -rn "catalogue_local" src --include=*.py`, and separately for `importlib`/`__import__` dynamic loads — none found), and `catalogue_local.py` refuses to run at all except under `--help` (per `drill.py:5123-5161`'s own net, `the_deprecated_cataloguer_still_refuses`). So no long-lived, codewatch-covered process has this module loaded in memory for codewatch's contract to protect. But codewatch's *purpose* — "a running process is a photograph of the code as it was when it started" — is a claim about `src/` as a whole, and if a future subdirectory under `src/` ever holds code a STANDING daemon does import (the project already has one non-deprecated subdirectory precedent risk if that convention changes), this blind spot would silently reproduce the exact incident codewatch.py exists to end.

**Proposed remedy**: switch both functions to `os.walk(root)` (skipping `__pycache__`, matching `liveness._modules()`'s and `drill._src_py_files()`'s fix), or add an explicit comment stating why top-level-only is intentional (e.g. "only `src/deprecated/` is a subdirectory and it is never imported live") so the choice is a ruling rather than a gap.

---

## FINDING 3 — QUESTION — src/foreman.py:1140-1211 (`restart_ollama`) — the post-restart "up" check re-uses the exact signal the function's own docstring names as insufficient

`restart_ollama`'s docstring (lines 1141-1148) says the wedge it exists to fix is: "twice in one day the daemon answered `/api/tags` while zero generations completed." The function's own success check after restarting (lines 1186-1194) is: poll `http://localhost:11434/api/tags` up to six times and set `up = True` on the first response — i.e. exactly the "answers `/api/tags`" signal the docstring says was insufficient evidence of health during the original wedge.

I am not filing this as a finding because the design has a real answer already built in: the remedy is rate-limited to one restart per 30 minutes (lines 1176-1179), so if `/api/tags` answers but tokens still do not flow, the *next* time this remedy is invoked (because the "the local model produces tokens" standard is still red) it hits the 30-minute gate and returns "restarted %.0f min ago and tokens still do not flow -- this is deeper than a wedge; owner attention needed" rather than restarting again — which does correctly stop this from silently looping forever on the insufficient signal. But the remedy's own success message ("ollama restarted (automated restart #%d); daemon answering, model reloads on first call") is reported as `did=True` for a round, which under `round_once`'s "did=True breaks the remedy list" rule (foreman.py:1843-1869) is fine here since neither of ollama's two standards has a second remedy in its list — but it is worth a second pair of eyes on whether "daemon answering" should count as `did=True` at all, given the docstring's own example of that exact signal being wrong.

**Proposed remedy**: none required if the 30-minute-gate safety-net reasoning above is accepted (I believe it is sufficient); if not, consider having `restart_ollama` make one throwaway generation call (bounded, cheap) before declaring `up=True`, matching the standard `"the local model produces tokens"` measures rather than the weaker liveness signal.

---

## FINDINGS FROM PARALLEL SUB-AGENT — src/catalogue_models.py, src/tells.py

Read in full (339 and 296 lines respectively, confirmed against `wc -l`). No stale line citations
in either file (both cite history by order-hash/run-number, never by line number, so Hard Rule 5
does not apply). No live Hard Rule 0 truncations (the only `[:N]` occurrences left in
`catalogue_models.py` are comments describing caps already removed by a prior fix; the
corresponding code was independently re-checked and confirmed uncapped). No `except: pass` /
fail-open swallow in either file.

- **QUESTION — src/catalogue_models.py:118-127 (`ask_provider`)** — a provider response whose
  rows use neither `id` nor `name` as a key produces an empty `ids` list and is classified
  `EMPTY_LIST` ("the API is alive and serves nothing") rather than as a parse failure, even
  though the API did serve rows. Flagged as a question because it depends on whether any real
  provider's `/v1/models` schema actually diverges from `{"id": ...}`/`{"name": ...}` in
  practice — not confirmed either way. Proposed remedy: if `rows` is non-empty but `ids` ends up
  empty, report a distinct outcome (e.g. `UNPARSEABLE`) instead of folding it into `EMPTY_LIST`.

- **QUESTION — src/catalogue_models.py:187-238 (`wanted`/`sweep`)** — a model entry in
  `cfg["models"]` whose `provider` value has no matching key in `cfg["providers"]` is invisible
  to every count `sweep()` produces (`want`'s per-provider loop only ever iterates
  `sorted(provs)`, i.e. names already in `cfg["providers"]`), which is the same "silently drops
  from the arithmetic" shape this file has fixed three times before (orders 1c5551aded53,
  cd64337d3349, sweep42-batch14) — but not confirmed to be a config shape that actually occurs
  in `~/cascade/config.json` (not read by the sub-agent). Proposed remedy: diff `want`'s provider
  keys against `provs` after building both and report any orphaned provider name as a distinct
  "referenced but not configured" row.

Everything else read in both files (the `LISTED`/`EMPTY_LIST`/`UNREACHABLE`/`UNCONFIGURED` outcome
split, the atomic `silence.write_json` gating, `tells.py`'s corruption guards, its `LEXICAL`/
`STRUCTURAL`/`DISCOURSE` pattern tables, `_anchor()`'s sentence-boundary rewrite, `prompt_in_sync()`'s
three-way honest verdict) checked out against the sub-agent's own verification notes and is not
repeated here.

---

## FINDINGS FROM PARALLEL SUB-AGENT — src/endpoint.py, src/tiers.py, src/recover_folder_records.py

Read in full (577, 542 and 379 lines respectively, confirmed against `wc -l`). I spot-verified
the sub-agent's two stale-citation claims and its two dormant-defect claims directly against
source myself (below) before including them; all four hold up. `recover_folder_records.py` grew
from ~289 lines at sweep47 to 379 here — the new material is a `short_sources`/`shortfalls`
mechanism (order 729c26e0e63c) which the sub-agent gave the closest read as the least-audited
code in the batch, cross-checking it against the real, current `FOLDER_SOURCE_MAP.json` (60
entries).

- **MINOR — src/tiers.py:386 (a second, sibling stale citation to Finding 1)** — `` That file
  is read by address_space AT IMPORT (address_space.py:129 and again in its main)``. I verified
  directly: `address_space.py:129` is prose ("universes had been DEFINED but never
  operationalised..."), not a read. The actual import-time read is `_tier_counts()`'s
  `with open(os.path.join(HERE, "data", "TIERS.json")...)` at **address_space.py:142**, called
  at module scope by `_TC = _tier_counts()` at **address_space.py:161**. The "and again in its
  main" half is accurate (main reads TIERS.json again around address_space.py:608-611).

- **MINOR — src/tiers.py:515-516 (a third stale citation, inside the very comment warning that
  line citations rot)** — `` This module states the rule as doctrine twice in the same words --
  "a tier that does not contain its own members is not a tier" (:111 and again at :156-157)``.
  I verified directly: line 111 and lines 156-157 of tiers.py contain neither this phrase nor
  anything resembling it (111 is about the charter's definition arriving "from the other
  direction"; 156-157 is the `CUTS` list literal). The phrase, and its near-twin ("does not
  contain its members"), actually appear at **tiers.py:142** and **tiers.py:204/524**.
  Between Finding 1's nine-plus-two count and this file's own three additional stale citations,
  eleven of the thirteen cross-file/cross-section line citations checked across this batch's
  eight files were wrong.

- **QUESTION — src/endpoint.py:475-482 (`source_pages`)** — collapses "no pages registered for
  this source" and "the registry file could not be read right now" into the same `[]` return,
  via a blanket `except Exception: return []`. Its sibling `register()` (same file, same
  `SOURCE_PAGES.json`) deliberately draws this exact distinction the other way — absent-file is
  `{}` (the truth), unreadable-file raises rather than silently proceeding ("we know nothing,
  and the only safe act is to not write," endpoint.py:499-501). `source_pages()`'s one live
  caller, `feats.reads_as_wiki()` (`src/feats.py:517`: `return not EP.source_pages(host[6:])`),
  would treat a transiently-unreadable registry as "this host has no registered pages" and flip
  a downstream wiki/non-wiki mining decision. Filed as a QUESTION rather than a finding because
  a bad READ here self-heals on the next call (unlike a bad write, which loses data permanently)
  — this may be a deliberate, lower-stakes asymmetry rather than an oversight, and I could not
  establish how often this file is actually read concurrently with a `register()` write in
  production. Proposed remedy: if not deliberate, distinguish absent-vs-unreadable the way
  `register()` already does, and have `reads_as_wiki` treat "unknown" as a refusal.

- **QUESTION — src/tiers.py:165-166** — `CUTS`/`MULTIVERSE_THRESHOLD`'s two invariant checks
  are bare module-level `assert` statements, which `python -O`/`PYTHONOPTIMIZE` strips entirely.
  Verified the two lines are plain `assert` as written. This project has already treated the
  identical hazard as worth fixing once (`scale_theories.py`'s equivalent invariant was
  deliberately rewritten as `raise` rather than `assert` specifically "so it survives `python
  -O`," per `handoff/sweep43/AUDIT_batch06.md`), but I found no evidence this pipeline is ever
  actually invoked with `-O` (grep across `src/` and `handoff/` for `-O`/`PYTHONOPTIMIZE` launch
  sites found none), so I cannot say this is live risk rather than a theoretical one. Proposed
  remedy: convert to `if not (...): raise AssertionError(...)` to match `scale_theories.py`'s
  own fix, or note in a comment that `-O` is never used to run this pipeline.

- **MINOR, unfiled-but-still-live** — **src/tiers.py:497** — `` print(f"   {s[:26]:<28}H..."`` in
  the SAMPLE STACKS block uses a bare `[:26]` slice with no truncation marker, unlike this same
  file's own `_cut()` helper (tiers.py:143-152, built for exactly this purpose and correctly
  used two blocks earlier at tiers.py:475 for the DELIBERATE JOINS table). Verified this is the
  only remaining bare `[:N]` slice in the file (the other two `grep` hits are historical
  docstring prose about already-fixed bugs). Currently dormant — the hardcoded sample-name list
  tops out at 17 characters — and this exact site was already named in
  `handoff/sweep45/AUDIT_batch16.md` under gathered order fe99e57e1993 as "a second site in the
  same file that neither order names." It is still present, unfixed, at its new line number;
  recorded here as a still-open item rather than a new one. Proposed remedy: `_cut(s, 26)` in
  place of `s[:26]`.

---

## What I read and found nothing wrong in

**src/foreman.py** — every AUTO-lane remedy (`clear_learned_caps`, `reprove_pool`, `adopt_hosts`,
`scout_hostless`, `rerun_roll`, `triage_swallowed`, `recatalogue_models`, `refresh_coverage`,
`kill_duplicate_jobs`, `_fandom_reachable`, `_catalogue_batch`, `run_catalogue_gap`,
`run_character_sweep`, `run_completeness_audit`, `run_charter_regression`); `kill_stalled_job`'s
`_restartable`/`_restart_horizon` gate pair (verified `_restartable` fails closed on an unreadable
roster and is derived from the same `_standing_cmds()` helper as `_restart_horizon`, so the two
cannot disagree); the whole MODEL-lane gate chain (`_function_source`'s qualified-scope
resolution, `_literals`/`regex_touched`'s regex-drift guard, `lines_changed`'s opcode-based
diff measurement, `_contracts_pass`'s shape-not-verdict CLI check, `_checks_pass`'s
read-the-number-not-the-substring `verify_math` gate and read-the-exit-code `allsweep --quick`
gate, `attempt_patch`'s backup/revert path including the "reverted" claim only being made when
the restore actually succeeds); `_retire`'s merge-through-`overwatch.save` path; `_pool_has_room`;
`owner_queue`'s uncapped blocked-URL listing and pid/thread-qualified atomic write;
`round_once`'s `always`-remedy handling and per-remedy exception isolation; `main()`'s fail-closed
escalation-chain import guard and loop-mode singleton/stamp/exit_if_stale sequencing.

**src/liveness.py** — the `scan()` DEAD/DEAD_CLASS/TAUTOLOGY/PHANTOM passes end to end, including
the receiver-aware `_credit_attrs`/`_scope_aliases` resolution and the MRO-by-name `scoped`
construction; the PHANTOM pass's widened test-site coverage (`if`/`while`/ternary/`assert`/
match-guard/short-circuit-statement/comprehension-filter) and its deliberately module-wide,
under-report-only `defined` set; `_modules()`'s `os.walk`-based traversal (itself the fix for the
same class Finding 2 raises about `codewatch.py`); the `reachability()` gate-coverage detector,
including its real-subprocess-under-`coverage.json` design (verified the `import coverage`
shadowing story against `src/coverage.py` actually existing), its fail-closed-on-every-error-path
behaviour, and `DECLARED_UNREACHABLE`'s name-not-line-number citation discipline; `main()`'s
itemisation-derived-from-the-same-tuple summary and its "kinds this report does not itemise"
overflow net.

**src/codewatch.py** — `coverage()`'s roster-derived (not hand-kept) KEEPER/COVERED/EXEMPT/
UNACCOUNTED classification, including the reportable-in-both-directions design (Finding filed
this shift as b67c5d98c91f, not re-reported here); `runs_script()`'s pure, drill-testable
command-line matching; `twins()`/`claim_singleton()`'s self-exclusion-is-additive-not-replacing
fix and fail-open-on-missing-`psutil` design; `stamp()`'s retry-then-escalate-loudly handling of
an unfingerprintable startup tree; the restart ledger's lock/budget chain (`_ledger_lock`,
`_take_locked`, `_claim_restart_slot`, `_record_restart`) including the fail-closed-on-a-denied-
write fix (order f06ba4c82363) and the check-and-take-under-one-lock fix (run #36); `stale()`'s
two-clock (`first_seen` vs `differing_since`) reasoning and its `quiet_seconds()`-vs-poll-history
corroboration against a backdated-mtime false positive; `_report_if_never_settling`'s rate
limiting and its MANAGER-unconditionally rank fix (order 13aee150e0dc); `exit_if_stale`'s
budget-spent-vs-ledger-denied distinction; `main()`'s union-of-roster-and-ledger reporting
(the b67c5d98c91f fix itself, audited as new code per the brief and found correct) and its
uncapped `_wrap()` reason-wrapping.

No `except: pass` or other silent fail-open swallow was found anywhere in the three
personally-read files beyond the ones already named, discussed and justified in their own
comments (e.g. `twins()`'s deliberate fail-open on a missing `psutil`, which is explicitly
reasoned about rather than accidental).

**src/endpoint.py** — the `data/ENDPOINTS.json` compare-and-swap merge in `_load()`/`_save()`
(digest-before-read ordering, `_DIRTY`-scoped merge rather than whole-snapshot overwrite,
retry/backoff, unlanded-save reporting), cross-checked against `silence.digest_of`/
`silence.replace_if_unchanged`'s real implementation; `UA_OVERRIDES`/`_get()`; `detect()`'s
DEAD_TTL expiry and API-then-raw probe ordering; `api_url()`/`raw_url()`; `fetch_raw()`'s
404/410-vs-other-refusal-vs-200-with-HTML-block-page handling; `main()`'s full-cache-listing
CLI; `MODE_HTML`/`html_text()`/`fetch_html()`; `register()`'s CAS write, its deliberate
raise-on-unreadable-vs-heal-on-absent distinction, and its thread/pid-qualified temp name; the
file-order guard confirmed to genuinely be the file's last statement.

**src/tiers.py** — the module docstring's narrative, confirmed internally consistent with its
own "these numbers are not to be read as current" caveats; `CUTS`/`MULTIVERSE_THRESHOLD`/
`DELIBERATE_JOIN` aside from the `-O` question above; `hyperverse_of()`, `xenoverse_grounding()`,
`GROUNDING_ORDER`; `_graph()`/`_components()`; `_load_groundings()`'s three-state
(readable/absent/corrupt) design, deliberately failing open at compute-time and closed at
publish-time; `chart()`'s per-source tier assembly and hyperverse-from-xenoverse
containment-by-construction; `deliberate_joins()`'s uncapped shared-evidence list; `main()`'s
two publish gates, including hand-tracing the `split_sources` containment scan to confirm the
threshold ordering cannot create a blind spot, and the `groundings_readable` re-check
immediately before the write; the write's verdict correctly reaching both the printed message
and the process exit code.

**src/recover_folder_records.py** — `load()` and the import-not-reimplement rationale for
`catalogue_aurora.record_path`/`slug`; `main()`'s argument parsing and register/source_map/roll
indexing; the `mapped is None` vs. `mapped == []` distinction driving `skipped_no_map` vs.
`skipped_no_items`; the new `shortfalls`/`short_sources` tracking, traced against the real
`FOLDER_SOURCE_MAP.json` for unpack or `None`-arithmetic errors (found none); the fail-closed
"already populated" guard (including its unreadable-file-counts-as-populated direction); record
construction and the provenance string's shortfall annex; the per-record write gate tracking
`silence.write_json`'s return into `denied`; the roll update via `roll.update_rows` (a
compare-and-swap merge, not a whole-snapshot land); and the reporting section, confirmed to
print every list uncapped and to surface a partial-write failure via `return 1 if denied else 0`.
Two items already flagged and explicitly not re-filed in prior sweeps (the `already = bool(...)`
TOCTOU window under open order 9a44b1535851, and `roll_by_name`'s unproven-but-unevidenced
name-uniqueness assumption from sweep46-batch05) were re-checked and correctly left alone rather
than re-reported.
