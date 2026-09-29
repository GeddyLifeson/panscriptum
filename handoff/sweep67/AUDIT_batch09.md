# sweep67 batch09 audit (run #67)

Read-only. Nothing under src/, data/, state/, output/, prompts/, reference/ or the repo root was
edited. No daemon, pipeline phase, generate/publish/mutate/verify_math/drill was run. No subagents.
Scratch scripts lived under %TEMP% only (fm_repro.py, bf_repro.py, on_repro.py, pf_chk.py,
nt_chk.py); the ones that import project modules stub os.kill, F.api or load_onomasticon.

## Scope (every line read with the Read tool, in chunks)

| module | lines |
|---|---|
| src/foreman.py | 2384 (4 chunks) |
| src/codewatch.py | 1247 (2 chunks) |
| src/onomast.py | 844 |
| src/build_terminal.py | 668 (incl. the JS template) |
| src/backfill.py | 536 |
| src/pantheon.py | 432 |
| src/profile.py | 354 |
| src/context_budget.py | 319 |

Line counts are up on sweep66 for foreman (2319 -> 2384), codewatch (1180 -> 1247) and backfill
(494 -> 536); the additions are the 2026-09-28 "fix everything" order fixes (see below).

## Prior-audit cross-check (sweep66 batch09/12/16/07/05/06)

state/workorders.json now holds 10 orders, all HOST_QUARANTINED or the one chain-index order; none
names any of these eight modules. Every earlier order that did has been closed. Verified in source:

- ff77e242b830 item 2 (restart_ollama books did=True on /api/tags alone): FIXED. `_ollama_generates()`
  (foreman.py:1401) now gates did=True on a completed generation.
- f7d7769075c0 (CODEWATCH_RESTART filed an order per granted restart): FIXED. codewatch.py:1091 files
  it at JANITOR with `order=False`.
- d9328fe1ee38 (stall detection reads the log only): still fixed, `_io_moving` present, and now also
  applied to the unrestartable branch (foreman.py:812).
- d1709d8e757d, 5bb12b398783, 6b59a5d4302a: no longer in the queue; nothing in these files.
- 0384c99d5454 (backfill `--all` exit code) and 21c075e5e2d6 (halt check on hand-run writers): FIXED in
  backfill.py (`_assert_not_halted`, rc=1 on errors or denied writes). Note `_INTERLOCKED` in
  verify_math is a one-way check (callers of assert_clear must be listed); nothing forces a new
  writer onto it (see Question 4).
- sweep66 cleared items for pantheon, profile, onomast, context_budget and backfill `roster()`:
  all re-traced this pass and still hold. Two are qualified below (F3, F7), same functions, a case
  the earlier pass did not trace.

## Findings

### F1. foreman.py:870-948 `kill_duplicate_jobs` identifies a "job" by script basename only, so it can SIGTERM the live daemon or a hand-run tool (MEDIUM, SUSPECTED design gap, reproduced)

`seen` is keyed on `re.search(r"src[\\/](\w+)\.py", line)` (line 888) and the OLDEST process per
basename is kept, the rest ended. The trigger, `standards` "one instance of each job"
(standards.py:2284), only checks seven fixed fragments, but the remedy applies to every script not in
`NEVER_DEDUPED` (read, pipeline, feats, catalogue_web, hostcheck, coverage ...) and compares scripts,
not jobs. `lognames.OWNER` fragments (`read.py --run`) and `codewatch.runs_script` (in-tree test)
both exist to make exactly this distinction and neither is used here.

Repro (fm_repro.py, os.kill stubbed so nothing was killed, scripted process table):

    100  ...\kit\src\read.py --run                       (oldest, the daemon)
    200  ...\kit\src\read.py --status                    (hand-run, newer)
    300  ...\tmp\sandbox\src\pipeline.py --run           (a mutate.py sandbox copy)
    400  ...\kit\src\pipeline.py --run                   (the LIVE pipeline)
    -> (True, 'ended duplicate read:200, pipeline:400')

So a person's `read.py --status` beside the daemon is killed, and the live pipeline is killed in
favour of an older sandbox copy of itself, because the tree is never looked at. `restart_reader`
(:650) and `kill_stalled_job` (:781) share the looser half of this (fragment match, no tree check),
so a sandboxed `read.py --run` is also a SIGTERM target for them.
Suggested fix: identify a job by its `lognames.OWNER` fragment plus
`codewatch.runs_script(argv, module, root=SRC, cwd=...)` for the tree, and compare like with like.

### F2. onomast.py:591-617 (`naming` excluded from `taken`) lets a NEW world take an existing world's published designation (LOW-MEDIUM, reproduced, needs a hash collision)

`taken` is seeded from prior records EXCEPT cids in `naming` (a collision group of two or more), on
the argument that seeding them would bump unchanged worlds. But those cids' standing designations are
then not reserved against a world that is added and sorts EARLIER by cid. That world is coined first
and, if its salt-0 name equals an existing one, takes it; the existing world walks to the next salt
and its designation changes. This is order 9309a040f208's failure ("every citation written against
run 1 now pointed at a different world") reached through addition instead of removal.

Repro (on_repro.py, `load_onomasticon` stubbed; colliding group id found by brute force, 12,003
tries):

    run1  c2=Oriamora  c9=Ilyira
    run2  (add c1 whose continuity group collides)  c1=Oriamora  c2=Alaelora  c9=Ilyira

Probability per added world is roughly (names already issued in that shelf) / (names per register,
some tens of thousands): small, not zero, across 26 Earths plus every other carried name and growth
over time. Suggested fix: when a cid in `naming` has a prior designation that is still well-formed
and not claimed by another cid, keep it; seed `taken` with the prior designation of every OTHER cid
(exclude only the cid being named).

### F3. backfill.py:88-97 `roster().members()` treats an API error body as an empty or short category (MEDIUM, reproduced)

`F.api` returns the parsed JSON for any HTTP 200. MediaWiki reports database errors, maxlag and
read-only mode as `200 {"error": {...}}`. `members()` raises `RosterIncomplete` only when `d` is
falsy; an error dict is truthy, `d.get("query", {}).get("categorymembers", [])` is empty, `cont` is
None, and the loop returns whatever it has. The docstring's promise ("this roster cannot be called
complete") is defeated for that whole class. The same silent short walk applies to the subcategory
pass, to later cmcontinue pages, and to the `prop=info` size probe (:212-224), where an error body is
not counted in `size_lookup_failed`.

Repro (bf_repro.py, `F.api` stubbed): first page returns Goku and Vegeta plus a continue token,
second page returns `{"error": {"code": "internal_api_error_DBQueryError"}}`. `roster()` returns
`['Goku', 'Vegeta']` with no exception, and `backfill_source` would print `roster 2 absent 0` as if
complete. Suggested fix: in `members()`, `if not d or "error" in d: raise RosterIncomplete(...)`, and
count `"error" in d` as a failed probe at :220.

### F4. backfill.py:201-203 the name key strips every non-ASCII-alphanumeric character, so distinct non-Latin titles collapse to the empty key (LOW, reproduced)

`re.sub(r"[^a-z0-9]+", "", name.lower())` turns any all-non-Latin name into `""` (checked: two
different Japanese names both give `''`). If the record holds any such entry, `"" in have` is True and
EVERY non-Latin-titled wiki page is judged already held and never fetched. Conversely, accented
names (Otsutsuki with a macron) key differently from their ASCII spelling and are added as
duplicates. No live source is known to be affected today, but the failure is silent and looks like a
small roster. Suggested fix: normalise with `unicodedata.normalize("NFKD", ...)` plus `str.isalnum()`
(keeps CJK), and never treat `""` as a key.

### F5. codewatch.py:699-702 `_record_restart` is dead, and two docstrings still describe it as the live path (LOW, dead code, stale comment)

No caller anywhere in src/ (grep of the tree: only the definition and comments). `exit_if_stale`
goes through `_claim_restart_slot` -> `_take_locked(enforce=True)`. `_ledger_lock`'s docstring
(:600-606) says `_record_restart` "reads the whole ledger ... and writes the whole ledger back" as the
thing being serialised, and `_claim_restart_slot`'s (:682) recounts it as a past hole; the
`enforce=False` arm of `_take_locked` is unreachable without it. Suggested fix: delete
`_record_restart` and the `enforce` parameter, or reword the `_ledger_lock` docstring to say
`_take_locked` is the writer.

### F6. foreman.py:1301-1302 a comment that belongs to `REMEDIES` sits above `RESTART_STAMP` (LOW, stale or misplaced comment)

"# standard name -> remedies to try, in order. A standard with no entry falls to the OWNER lane ..."
heads the ollama-restart constants; the dict it describes is at :1573 (which has its own comment).
It reads as if `RESTART_STAMP` were the table.

### F7. profile.py:132, 227-228 unknown genre or register codes are answered with a plausible value instead of refused (LOW, dormant)

`encode` maps an unknown genre to "un" and an unknown register to "c" (classical) with no
`silence.note`; `decode` maps an unknown two-letter genre code or register letter to "unclassified"
or "classical". Verified: `decode("PS-1-zzc-0000-u0")` returns genre `unclassified`, and
`encode(1, "nonsense", "alsobad", ...)` returns `PS-1-unc-0000-u0`. This is the shape of the owner's
2026-09-08 "answering unknown with a plausible value" ruling, beside a `decode` that otherwise refuses
readably (alphabet, feature digits, band, attested). Dormant: all 210 sources in GENRES.json carry
both genre and register, and all 157 sources behind the live worlds are present in GENRES.json and
TIERS.json, so no live path reaches it (`build_all`'s `register` default of "classical" at :266 has
the same property). Suggested fix: note the fallback in `encode`, and make `decode` refuse a code
that is not in `GENRE_FROM` or `REG_FROM`.

### F8. context_budget.py:29-32, 82-88 the header and constant comments quote measurements of a prompt file that has since changed (LOW, stale comment)

"lines 1-102 ... (6,964 chars) ... lines 103-245 ... THE ENTRY TEMPLATE (11,147 chars)" and "the
18,112-char system prompt". The live prompts/system_style.txt is 270 lines and 20,544 bytes, the
template heading is at line 129, and the voice half is about 9,249 bytes. The code locates the
heading by text (correctly, per its own note), so behaviour is right; only the quoted numbers are
out of date, and they are the ones a reader would reason from. Suggested fix: mark them "as measured
2026-08-24".

## Questions

1. foreman.py:295 `SC.sweep(limit=4)` in `scout_hostless`. `_catalogue_batch`'s docstring (:1019)
   says the owner abolished the non-rotating `scout.sweep(limit=4)` window on 2026-08-25, yet the call
   still passes `limit=4`. Was `limit` made a rate inside `scout.sweep` (rotating), or is the head of
   the hostless list still the only part ever tried? (scout.py is outside this batch, not read.)
2. foreman.py:1979-1992 `attempt_patch` writes the patched module with a bare `open(path, "w")` and
   restores with a bare `shutil.copy2`, not `replace_retry`. A daemon importing the module during the
   minutes-long `_checks_pass` window can read a model-authored, unverified body, and a torn file if
   the process dies mid-write. Deliberate for the DENYLIST-fenced model lane (a backup exists), or
   should the write and the revert go through the atomic helper?
3. backfill.py:115-119 walks exactly ONE level of subcategory under Category:Characters. A roster
   nested two levels ("Characters > Villains > Marvel Villains") is silently short and reported as
   complete. It is documented ("one level of subcategory is walked too"), but it is a depth cap in
   Hard Rule 0's sense. Intended?
4. pantheon.py, onomast.py and build_terminal.py write data/PANTHEON.json, data/ONOMASTICON.json and
   output/registry_terminal.html with no `escalation.assert_clear`. They are derivations, not corpus
   writers, so I did not file them; but onomast is append-only and both its writers are
   corpus-adjacent. Should the halt-interlock roster (verify_math `_INTERLOCKED`, the drill net)
   extend to derived-state writers, or stop at the corpus?
5. build_terminal.py:616-629 splices data/NAVTREE.json text into the page without parsing it. A torn
   or truncated NAVTREE writes a page that fails at load and returns rc 0. NAVTREE is written
   atomically upstream, so this is latent; is a `json.loads` gate wanted here?

## Cleared (traced, no defect)

- foreman.py: `clear_learned_caps` json_extract predicate and unreadable-db arm; `reprove_pool`
  did=False on zero answering; `adopt_hosts` non-zero-count regex; `triage_swallowed`
  archive-then-clear ordering with both writes gated; `_standing_cmds`, `_restartable`,
  `_restart_horizon` shared derivation and fail-closed; `_python_processes` fail-closed on a blind
  table; `_io_moving` only narrows; `_retire_stall_order` id math and both call sites;
  `_catalogue_batch` (whole universe, last-dispatched-first ordering, rate not filter,
  printed-by-name deferral, fragment uniqueness against catalogue_web's own identical gap filter,
  stamp before work); `restart_ollama` stamp fail-closed on unreadable, tray-absent path, gated
  did=True; `_literals`, `lines_changed`, `regex_touched`; `_contracts_pass` shape-only grading;
  `_checks_pass` numeric read of the FAILED count and rc-based allsweep gate; `round_once` `.always`
  continuation and remedy exceptions; `owner_queue` all URLs and pid/thread scratch name; `main`
  per-round halt re-ask, singleton claim only in loop mode, rc=1 on halt. `ON.running(...)` is a
  strict script-argument match (overnight._cmd_is_running), so `running("sweep.py")` does not match
  `allsweep.py`.
- codewatch.py: `_py_tree` (raises on an unlistable dir, prunes __pycache__), `fingerprint` and
  `quiet_seconds` None-is-not-unchanged, `stale()` two-clock logic and stamp corroboration,
  `runs_script`, `twins` and `claim_singleton` self-exclusion, `stamp` retry and MANAGER escalation
  on a blind stamp, `_take_locked` fail-closed on a denied ledger write, `_ledger_lock`
  PermissionError arm, `_poll_pid_alive` three-valued answer, `exit_if_stale` budget vs
  ledger-denied split, `exit_if_paused` roster, `main()` union report.
- onomast.py: `well_formed` (seven constraints match the docstring), `coin_name` determinism,
  `coin_well_formed_stamped` unique-by-construction last resort, `load_onomasticon`
  missing-vs-unreadable, `land_onomasticon` digest CAS with re-run on a moved file, standing-vs-
  retired split, `main` exit code carries a refused write. (Apart from F2.)
- build_terminal.py: every `esc()` sink, `trimmed()` marked cuts with the full text in the tooltip and
  panel, layout and weight math, roster kept uncapped (scroll, not slice), `<` neutralisation before
  the inline script, atomic write with the denial in the exit code and temp cleanup, `--help` does
  not rebuild. NAVTREE has every field the JS reads (734 nodes, 1,569 worlds, integer seeds, none
  missing k/n/src/t).
- backfill.py: `lead()` marked cuts, size-rank key `(t in sizes, -size)`, `--cap` opt-in with `absent`
  reported pre-cap, `write_record_catalogue` gating, `--all` and `--source` per-source containment
  and rc, halt check only on the writing path. (Apart from F3, F4.)
- pantheon.py: `compute` and `value`, merge failure modes and rc, `_incomplete` marker, band label
  table M0-M10, uncapped `--full` view with wrapped citations. Minor: the "MERGE FAILED" line says the
  ranking is the hand-built gods alone, which would be inaccurate if a failure came after some
  entries were folded in; not reachable today (`json.load` fails before any `setdefault`).
- profile.py: `_B32_CLASS` regex built from the alphabet, `decode` per-axis range refusal, band clamp
  and index pairing (B32[10] = "a" = M10), `encode` refusal of a bad `attested`, round-trip check
  re-encodes rather than comparing a string with itself. (Apart from F7.)
- context_budget.py: fail-closed `_read_scaffold`, budget may go zero or negative without clamping,
  prose vs content ratios, `window()` fallback 6144, `split_system_prompt` on the heading (single
  occurrence at line 129 of the live prompt). (Apart from F8.)
