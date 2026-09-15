# Sweep 59 -- AUDIT batch 11

Modules read in full: | module | lines | read (top to bottom? mtime) |
| overnight.py | 2006 | yes, top to bottom (mtime 2026-09-13 23:50) |
| codewatch.py | 1164 at read time, 1168 now (edited under me mid-shift, +4 lines; no finding below cites a line in the changed region) | yes, top to bottom (read at mtime 2026-09-14 00:21; re-checked def-list after it moved to 22:26) |
| completeness.py | 871 | yes, top to bottom (mtime 2026-09-13 23:39) |
| thread_integrity.py | 721 | yes, top to bottom (mtime 2026-09-07 23:16) |
| tiers.py | 554 | yes, top to bottom (mtime 2026-09-14 00:01) |
| cleanup.py | 452 | yes, top to bottom (mtime 2026-09-14 22:14) |
| sweep.py | 374 | yes, top to bottom (mtime 2026-09-08 16:26) |
| physics.py | 312 | yes, top to bottom (mtime 2026-09-06 22:34) |

## Special assignment: how the keeper spawns standing daemons, and the publish/gh.exe exec failure

`src/publish.py` (not one of my modules, read only for cross-reference) already carries the
live symptom in its own docstrings: `_credential_probe` (added tonight, run #59) records that
"from 18:00 on 2026-09-14 the standing `--push --loop` daemon logged every cycle
`'.../gh-cli/bin/gh.exe' auth git-credential get: line 1: ...gh.exe: No such file or
directory' while gh.exe was on disk" and that "maintenance run #59 could NOT reproduce it: this
function's exact environment (read from the daemon with psutil), and a detached, windowless
pythonw carrying it, both pushed cleanly. So the difference is in the daemon's process context,
not in its variables." `publish.git()` (src/publish.py:745-748) already strips
GITHUB_TOKEN/GH_TOKEN and explicitly appends the gh-cli directory to PATH, so the two
environment-variable explanations are already closed off by tonight's own work.

**QUESTION -- the one process-context difference `_guarded_popen` actually has, versus a
directly-run process, is that stdin is never set** (two readings, needs a ruling / a live repro
to confirm causation, so filed as a question rather than a defect)

where: `src/overnight.py` `_guarded_popen` lines 514-517 (mtime 23:50) -- the SOLE spawn site
for every STANDING daemon, `publish` included (`start("publish", ...)` at line 1756 calls
`start()` -> `_guarded_popen()`):

```
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        p = subprocess.Popen([PY, "-u", *args], cwd=HERE, stdout=fh,
                             stderr=subprocess.STDOUT, env=env,
                             creationflags=NO_WINDOW)
```

`stdout`/`stderr` are always explicit (redirected to the job's own log file); `stdin` is never
given a value here, in `run()`'s twin call, or in `publish.git()`'s own subprocess call
(`src/publish.py:749-750`, `capture_output=True` sets stdout/stderr to PIPE but never touches
stdin either). On Windows, when a `Popen` call redirects only some of stdin/stdout/stderr,
CPython's Win32 backend fills the unspecified ones with the CALLING PROCESS's own
`GetStdHandle()` values and marks them inheritable for the child (this is why `stdout=fh` alone
is enough to make the child's stdout the log file, but the sibling stdin is whatever handle the
supervisor itself is holding). `overnight.py` itself is a STANDING-adjacent process started
windowless (`_NO_WIN`/`CREATE_NO_WINDOW` throughout this file; its own docstring at line 442-443
notes `DETACHED_PROCESS is deliberately NOT set here ... these children are joined`) by
`autostart.py`'s watchdog, which per this file's own comment (main(), lines 1493-1495) is itself
started at logon by the Startup `.vbs`. If that whole ancestry has never had a real console,
`overnight.py`'s own stdin handle is plausibly null/invalid, and `_guarded_popen` hands that
same handle down to `publish.py`, which hands it down again (via its own unset-stdin
`subprocess.run` for `git`) to `git.exe`, and from there to whatever spawns the credential
helper. A directly "session-spawned" process (typed into a live terminal, or a manually-started
test) always has a real console and a real stdin handle the whole way down, which is exactly
the asymmetry `_credential_probe`'s docstring reports and could not explain from the
environment. `_credential_probe`'s "detached, windowless pythonw" reproduction attempt that
pushed cleanly is not the same code path as `_guarded_popen`: this file's own comment says
DETACHED_PROCESS is deliberately not used for the real daemons, so that successful test used a
different creation flag from the one the real `publish` daemon runs under, and is not evidence
against this hypothesis.

remedy, if a live repro confirms it: add `stdin=subprocess.DEVNULL` to `_guarded_popen`'s
`Popen(...)` call at `src/overnight.py:515-517`. `DEVNULL` is always a valid handle regardless
of the supervisor's own console ancestry, so it removes the invalid-inherited-handle
possibility outright rather than depending on what the supervisor happened to inherit at boot.
This is a one-line, low-risk change to the single spawn site every STANDING daemon (dashboard,
publish, foreman, overwatch, pipeline, read) already goes through.

Not filed as a DEFECT because it cannot be verified against source alone -- it requires either
a live repro with `stdin=subprocess.DEVNULL` added, or capturing the actual stdin handle value
of a running `publish.py` restarted by the keeper (e.g. via a psutil/handle inspection from
inside that exact process, the same technique `_credential_probe` already uses for environment).
No job object, `CreateJobObject`, or handle-list API is used anywhere in `src/` (grepped the
whole tree; zero hits), so job objects are not implicated. `creationflags` is uniformly
`CREATE_NO_WINDOW` for every Popen site in `overnight.py`; the DETACHED_PROCESS distinction
above is the only creationflags-adjacent difference this file's own comments admit to.

## overnight.py
### New findings
See the special assignment above (the `_guarded_popen` stdin question). No other new findings;
this module has been swept repeatedly (dozens of "order" citations for defects already fixed in
place) and a full top-to-bottom read found nothing further to add.

### Known (already open orders)
- `018727423a09`, `764e283cdf00`, `91bb70c85e31`, `e45618de083f`, `ee382241ff8c` (CODEWATCH_RESTART, INFO) -- still accurate, all "mechanism working, not a fault" per `f7d7769075c0`'s own framing; not re-filed.
- `f7d7769075c0` (CODEWATCH_RESTART_FILES_AN_ORDER_PER_DESIGNED_RESTART) -- still open, still an owner ruling question (whether the threshold moves to over-budget-only); the code is unchanged since it was filed.
- `d1709d8e757d` (ENTITY_INDEX_NEVER_REBUILT...) -- still accurate: `overnight.STANDING` still does not include `weave_index`, and no `weave_index_cycle()` exists in `main()`'s cycle body (verified by reading the whole cycle body, lines 1662-2001: `canon_backup_cycle()` and `identity_refresh_cycle()` are there, no weave_index call). Still an owner-routed ruling, not re-filed.

### Checked and clean
- `_guarded_popen`'s lock (`_SPAWN_LOCK`) genuinely serialises the authoritative `running()` check with the spawn; the double-checked-locking race the docstring describes is closed.
- `stale`/`running`/`_in_this_tree`/`_cmd_is_running` quote-aware tokenising (`_cmd_tokens`) correctly handles the Startup `.vbs`'s quoted launch line; verified the `-m`/`-c` exclusions and the samefile-vs-normcase fallback.
- `name_rc`'s NTSTATUS table and the rc=17 special-case are consistent with `codewatch.RC_STALE`.
- `main()`'s halt-handling: the fail-closed default (`_halted = True` on an unreadable `escalation.status()`) and the "wait, don't exit" behaviour on IDLE_LIMIT are both present and match the doctrine in CLAUDE.md Hard Rule -1.
- `ALL_JOBS`/`STANDING` construction is derived, not hand-duplicated, and `codewatch.coverage()`'s basename comparison against it lines up.

## codewatch.py
### New findings
None. Full top-to-bottom read found this module's restart-budget locking (`_ledger_lock`,
`_take_locked`, `_claim_restart_slot`), its settle-window arithmetic (`stale()`'s
`quiet_seconds()`-vs-`first_seen` reconciliation), and its poll-liveness three-valued logic
(`_poll_pid_alive`) all internally consistent and already hardened against the specific races
their own comments describe. The file changed under me mid-read (1164 -> 1168 lines, mtime
00:21 -> 22:26); re-checked the function list afterward and nothing I cite above moved into
the changed region.

### Known (already open orders)
None of my modules' names appear against an open order specific to codewatch.py beyond the
CODEWATCH_RESTART/`f7d7769075c0` family already listed under overnight.py above (codewatch.py
is the module named in `where` for `f7d7769075c0`, restated there rather than twice).

### Checked and clean
- `runs_script()`'s `-m`/`-c` handling and its samefile-then-normcase fallback for a reaped sandbox path.
- `twins()`'s self-exclusion (`skip = {os.getpid()}` plus `exclude_pid`, additive not replacing).
- `_claim_restart_slot`'s single locked check-and-take (no separate read-then-write window).
- `_report_if_never_settling`'s rate-limiting (`_PENDING["said_at"]`) and unconditional MANAGER rank.

## completeness.py
### New findings

**DEFECT MAJOR -- `if n:` conflates "category confirmed absent" with "category confirmed
present, zero direct member pages", so a subcat-organized character roster can report a
fabricated tiny denominator or a false "no such category" verdict**

where: `src/completeness.py` `audit.work` lines 549 and 556 (mtime 23:39):

```
545:        if sub:
546:            for cand in probes:
547:                n, err = category_size_probe(sub, cand)
548:                if err:
549:                    failed += 1
550:                if n:
551:                    sizes[cand] = n
552:        elif api_base(host):
553:            for cand in probes:
554:                n, err = category_size_probe_host(host, cand)
555:                if err:
556:                    failed += 1
557:                if n:
558:                    sizes[cand] = n
```

evidence: `category_size_probe`/`category_size_probe_host` return `(got, None)` where `got =
ci.get("pages", 0)` whenever the MediaWiki category page has ANY members (pages, subcats, or
files) -- `got` can be legitimately `0` when a category holds subcategories but no direct
pages, which is exactly how many wikis organise a "Characters" category (arc/season
sub-buckets, no members filed directly under the parent). `if n:` treats that `0` identically
to `None` ("no such category"), so it is silently dropped from `sizes` rather than recorded as
a real (if useless-as-a-max) measurement. This is not hypothetical on this corpus:
`state/category_sizes.json` currently holds 20 cached probes with `n: 0` (e.g.
`onepiece|Characters`, `xenoblade|Characters`, `xenoblade|Heroes`, `pixar|People`,
`lovecraft|Characters`, `en.wikipedia.org|Characters`). Pulling the full One Piece row from that
same cache:

```
onepiece|Characters {'n': 0}      onepiece|Antagonists {'n': 1}
onepiece|People {'n': None}       onepiece|Villains {'n': None}
onepiece|Protagonists {'n': None} onepiece|Heroes {'n': None}
onepiece|Major Characters {'n': None}   onepiece|Playable characters {'n': None}
```

failure: with `if n:`, every candidate above except `Antagonists` (n=1) is excluded from
`sizes` -- including `Characters`, which DOES exist and DOES hold real content, just not as
direct pages. `best = max(sizes.values())` then becomes `1`, so `wiki_persons` for a franchise
with a real cast in the hundreds is reported as `1`. If `catalogued_persons` for that source is
anything greater than 1 (One Piece's is; `data/COMPLETENESS.json` currently shows
`catalogued_persons: 321` under a different, "host unreachable", row for the same source), the
`cov > 1.0` branch usually catches the resulting nonsense and flags it as "the probe list missed
this wiki's real category name" -- but that safety net is not guaranteed: if `catalogued_persons`
for a source happens to be `<= best` (e.g. a lightly-catalogued or as-yet-uncatalogued source
whose real cast is organised the same way), the row lands as ordinary, believed-measured,
`unreliable: None` with a `coverage` figure computed against a denominator of `1` -- or, if every
probe for that source comes back `n=0`/`None` with zero transport failures, the row instead takes
the `if not sizes and failed == 0:` "genuine absence" branch (`src/completeness.py:616-622`) and
states outright that "none of the N CATEGORY_PROBES categories exists on %s", which is false: the
categories exist, they simply hold their members via subcategories rather than direct pages.

remedy: change `if n:` to `if n is not None:` at both sites (549, 556), so a real zero is
recorded in `sizes` as a real zero rather than silently discarded to the same bucket as "no such
category". This alone will not make subcat-organized rosters countable -- that is the same
"probe list missed the real category" limitation `cov > 1.0`'s own comment already documents --
but it stops a genuine zero measurement from masquerading as a genuinely wrong tiny nonzero
`best`, and stops the "genuine absence" branch from asserting a category doesn't exist when the
probe cache shows it does.

### Known (already open orders)
- `f5b8e4afb558` (PRIMARY_HOST_ONLY_EVER_FANDOM) -- still accurate. Remedy (a) is landed and
  verified live in the current source at lines 671-676 (the non-fandom "no primary can be
  identified... the question was never asked" wording is present exactly as the order's shift
  note describes); remedy (b) (what SHOULD decide the primary for a shared non-fandom host) is
  still an open owner ruling. Not re-filed.

### Checked and clean
- `land()`'s three-valued verdict (`True`/`False`/`SKIPPED_ONLY`) and the SHRINK_FLOOR guard are both wired correctly into `main()`'s `if not verdict / elif unwritten / if verdict is True` branches.
- `host_reachable()`'s three-mode (`MODE_RAW`/`MODE_DEAD`/api) handling matches its own docstring's incident history.
- `wiki_host()`'s sentinel/whitespace/scheme rejection is applied consistently before any network probe.
- `_cs_put`'s per-process-and-thread temp filename and lock-protected snapshot-then-serialise correctly avoid the two-writers-one-tempfile hazard its docstring describes.

## thread_integrity.py
### New findings
None beyond the already-open order below (re-verified against current source, not re-filed).

### Known (already open orders)
- `a724ec57e0d5` (TI_DANGLING_VERDICT_STOPS_SHORT_OF_THE_LADDER) -- still accurate as filed.
  Verified against the current file: `main()` computes `dangling = counts.get("DANGLING", 0)`
  at line 646, prints a FAILED message and sets `failed = bool(dangling)` at line 657, and calls
  no `escalation.escalate()` for DANGLING anywhere in the function -- while the sibling
  SUPERVISOR/THREAD_UNRESOLVABLE branch four lines below (lines 663-683) does escalate, per
  source, citing STEP4_PLAN.md section 8 by name, exactly as the order's evidence describes.
  Still a two-reading ruling question per the order's own text, not re-filed.

### Checked and clean
- `classify()`'s directed-pair dedup (`seen`) and the `(b,a) in seen` mirror check are correct; `(a,a)` cannot occur by construction, matching the comment at line ~358.
- `load_thread_graph()`'s fail-closed `ThreadGraphUnreadable` (raised, never silently empty) versus the legitimate `None` for an absent file.
- `_floor_verdict`'s six-state ratchet (baseline/UNRECORDABLE/held/ratcheted/held-unrecorded/REGRESSED/UNREADABLE) matches its own docstring table exactly.
- `_charter_codes()`/`_charter_codes_corrupt()` correctly distinguish an absent charter file (silent) from a present-but-corrupt one (JANITOR escalation), per order d56c041a8f4d.

## tiers.py
### New findings
None. Full top-to-bottom read; this module's invariants (`CUTS` loosening downward, the
multiverse/metaverse/xenoverse containment scan, the `xenoverse_grounding` per-xenoverse pooling)
all check out against their own stated logic and are already gated (refuses to write
`TIERS.json` on an unreadable `GROUNDINGS.json` or a containment violation).

### Checked and clean
- `_components()` (single-linkage BFS) versus `weave.components()` (complete-linkage, used only for the multiverse) are deliberately different algorithms per the module's own doctrine, and `chart()` uses each in the right place.
- The 99.5th-percentile integer-arithmetic ceiling (`rank = max(1, -((-995 * len(vals)) // 1000))`) is the correct ceiling-division formula.
- `main()`'s write gating on both `groundings_readable` and `split_sources` (containment) before touching `data/TIERS.json`, with the exit code tracking the write verdict (`ok`) rather than the chart verdict.

## cleanup.py
### New findings
None. Full top-to-bottom read; every non-trivial regex and matching function
(`_ruby_question_mark`, `_ruby_parenthetical`, `clean_ceiling`'s exact/head/prefix ladder) is
already extensively fixed and commented with the false positives that were measured and closed.

### Checked and clean
- The mangled-escape guard loop (`for _n, _p in (...)`) correctly covers `_NAV`, `_EMPTY_MECHANIC`, `_SETTING_META` (imported from `pipeline`), and every compiled pattern in `_MARKUP`.
- `clean_ceiling`'s prefix-ambiguous branch (`len(low_pref) > 1`) is reported separately from `unresolved`, and the candidates are recomputed at the print site rather than smuggled through the two-value return contract.
- `main()`'s per-entry `continue` after a nav/mechanic exclusion correctly prevents a struck entry from also being scored for description cleanup or thinness.
- The `thin_description` mark-once guard (`not e.get("thin_description")`) correctly stops a no-op rewrite on every subsequent `--apply` run while still reporting every thin entry found.

## sweep.py
### New findings
None. Full top-to-bottom read.

### Checked and clean
- `nested_run()`'s greedy longest-consecutive-nested-run scan over `STAGE_TESTS` is correct for what `report()` uses it for (drawing a funnel only over stages that really do nest, per-run, rather than asserting nesting).
- `rosetta_index()`'s finer-grained-scale-wins tie-break (`sc["n"] > idx[k][3]`) matches its docstring.
- `report()`'s uncapped BIGGEST GAPS / REACHED BUT SILENT rosters and the padded-not-cut `DEEPEST EVIDENCE` table are consistent with Hard Rule 0.
- `main()`'s gated `silence.write_json` call with a stderr message and nonzero return on a denied replace.

## physics.py
### New findings
None. Full top-to-bottom read.

### Checked and clean
- `kinetic()`, `joules_for()`, `sphere_volume()`, `binding_energy()` each refuse non-positive, non-finite, and (where applicable) NaN inputs, and each also checks its OWN result for non-finiteness (the "result, not just the argument" pattern documented at length in-file) -- verified all four functions actually implement what their own comments claim, not just the comments.
- The relativistic/Newtonian switch in `kinetic()` at `RELATIVISTIC_ABOVE * C` is a clean `<` boundary with no gap or double-count at the threshold.

QUESTIONS: 1
record(): ok
