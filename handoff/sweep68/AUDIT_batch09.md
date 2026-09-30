# sweep68 batch09 audit (run #68)

Read-only. Nothing under src/, data/, state/, output/, prompts/ or config.yaml was edited. No daemon,
pipeline phase, generate/publish/mutate/verify_math/drill was run; no subagents. Scratch scripts are in
`%TEMP%/aud68_09` (t1-t13). Reproductions that import project modules redirect their write paths to a
temp dir or stub `os.kill`/`_python_processes`; t2 and t12 only READ the live process table and data.

## Scope (every line read with the Read tool, in chunks)

| module | lines |
|---|---|
| src/foreman.py | 2417 |
| src/codewatch.py | 1251 |
| src/catalogue_web.py | 872 |
| src/build_terminal.py | 668 (incl. the JS template) |
| src/backfill.py | 546 |
| src/burgs.py | 472 |
| src/tells.py | 352 |
| src/tempus.py | 309 |

## Prior-audit cross-check (sweep67 batches 03, 09, 11, 15, 16)

| prior item | status now |
|---|---|
| b09 F1 `kill_duplicate_jobs` keyed on script basename | Fixed in intent (`_foreign_prefix`, args in the key), **but the fix is broken for every absolute-path job: see F1 below.** |
| b09 F3 backfill `members()` treats an API error body as empty | Fixed at the root: `feats.api` now returns None on any `{"error": ...}` 200 (feats.py ~:891-900), so `if not d: raise RosterIncomplete` fires. Size probe counts `d is None`. Holds. |
| b09 F4 backfill name key collapses non-Latin | Fixed (`_name_key`, NFKD + isalnum). Small residue: F8. The same defect is still live in catalogue_web (F2). |
| b09 F5 codewatch `_record_restart` dead, docstrings lie | Fixed by wording (docstrings now say `_take_locked` is the writer, `_record_restart` is a test entry). |
| b09 F6 misplaced REMEDIES comment | Fixed (comment now sits above `REMEDIES`, foreman.py:1603). |
| b09 Q1 `SC.sweep(limit=4)` | Still there (foreman.py:296); scout.py not in this batch. Unchanged question. |
| b09 Q2 `attempt_patch` bare `open(path,"w")` + `copy2` revert | Still there (foreman.py:2016-2024). Unchanged question. |
| b09 Q3 backfill walks one subcategory level only | Still there (backfill.py:116). Unchanged question. |
| b09 Q4 build_terminal has no halt interlock | Still none. Unchanged. |
| b09 Q5 build_terminal splices NAVTREE text unparsed | Reproduced this run: F5. |
| b03 F7 catalogue_web no-text title shadows twins | Fixed (`_dedup_fetch` claims a key only for a title that produced text; twins re-fetched). Traced the twin promotion loop, including the trailing `seen[key]` lookup (never evaluated for an empty `rest`). Holds. |
| b03 F8 `_singular` -zes/-ches | Fixed ("zes"/"ches" removed; comment at :154). |
| b03 catalogue_web dead `MAX_PER_CATEGORY`/`CATEGORY_SCAN_DEPTH` | Still dead-but-marked, as ruled. |
| b15 tells F6 (missing `\b` on two patterns) / F7 (double count, inflections) | Fixed (`\bstands?` at :101/:134; `_INFLECT`, span suppression in `scan`). |
| b15 tells DISCOURSE anchor import guard | Present and correct. |
| b11 burgs halt guard | Present (`_assert_not_halted`, `--write` only). |
| b16 tempus Q4 unknown shelf == "no path" | Still stands, reproduced (F7). |

New since sweep67: tells.py grew 319 -> 352 (2026-09-29 additions, order 2fe8078a0d0e). Verified:
`tells.prompt_in_sync()` returns True (all 158 entries present in prompts/system_style.txt), the new patterns
compile and fire on their intended shapes, and the span-suppression still applies. See F9 for one stale
count the additions left behind.

## Findings

### F1. HIGH (reproduced live) - foreman.py:604 `_SCRIPT_RE` reads the python.exe path as part of the script prefix, so `_foreign_tree` is True for every job launched with an absolute script path

Quote: `r'([A-Za-z]:[\\/][^"]*?[\\/])?src[\\/](\w+)\.py"?(.*)$'`

`list2cmdline` quotes only arguments containing spaces. The live commands are
`C:\Users\imarl\miniconda3\pythonw.exe -u C:\...\panscriptum-library-kit\src\publish.py --push --loop 10`
(nothing quoted). `re.search` scans from position 0, the optional group starts at the interpreter's `C:\`,
and `[^"]*?` (no whitespace exclusion) lazily runs across the space to the `src\`, so group(1) is
`C:\Users\imarl\miniconda3\python.exe C:\...\kit\`. `_foreign_prefix` then compares
`normpath(that + "src")` with `SRC`, finds a mismatch, and calls the tree foreign.

Failure scenario. `overnight.STANDING` builds every entry with `os.path.join(SRC, "<x>.py")`, so all of
dashboard, publish, foreman, overwatch, pipeline and read run with an absolute script path (and so do
autostart and the crawl). Every one is "another tree's process", so:
- `restart_reader` (:673) skips the live `read.py --run` and returns
  `(False, 'reader is not running -- read.py --run is STANDING, so the keeper restarts it within 300s')`, a false
  sentence about a running reader, for the standard "the library's counters are moving";
- `kill_stalled_job` (:803) never finds a stalled STANDING job or the crawl, so it ends
  `stalled jobs found but no process matched`;
- `kill_duplicate_jobs` (:921) `continue`s past every absolute-path twin: `(True, 'no duplicates found now')`
  with two `pipeline.py --run` alive.

Reproduction. `t2.py` (read-only, live table): `publish.py`, `dashboard.py`, `feats.py --roll`,
`autostart.py`, `coverage.py`, `verify_math.py` all print `foreign= True`; only the `src/...`-relative
ones (magnitude, drill, allsweep) print False. `t11.py` (scripted table, `os.kill` stubbed): with realistic
absolute lines `restart_reader` -> the false "not running" answer, `kill_duplicate_jobs` -> nothing ended;
the same table with `src\` relative paths -> reader bounced (pid 100), duplicate pipeline:300 ended.

Why nothing went red: `drill._dedupe_ends_only_a_true_twin` (drill.py:3772) scripts its rows as
`'"py" "%s" --run'`, i.e. BOTH the interpreter and the script quoted, a shape `list2cmdline` never
produces for these paths, so the prefix group can only start at the script. The net cannot fail against the
real command line (the same "scripted the listing, so none could see it" class the neighbouring docstring
records for order 7bd2ee5f8b3b). Suggested fix: exclude whitespace from the unquoted-prefix class (and match a
quoted path as its own alternative), and drive the net with `subprocess.list2cmdline([sys.executable, script,
...])` rows. This was introduced by the sweep67 F1 remedy (order 2a5344d24132).

### F2. MEDIUM (reproduced mechanism; live exposure unproven) - catalogue_web.py:175-181 `_dedup_fetch._key` strips everything outside `[a-z0-9]`, so a title with no Latin letters or digits is dropped with no trace

Quote: `return re.sub(r"[^a-z0-9]", "", t.lower())` ... `if not key: continue`

Same defect backfill fixed under order 5032684974ff (`_name_key`, NFKD + `isalnum`), left behind here.
Scenario: a category listing holds `東京`, `ゴクウ`, `Гоку`. Each keys to `""`, is skipped before `fetched`,
before `deduped`, and before `no_text`, so no counter, provenance line or log names it: `catalogue()` reports
`ok` for the source. `t4.py`: asked 6, fetched `['Goku','Ōkami']`, deduped `[('Kami','Ōkami')]`, and the
three non-Latin titles appear in neither list. Accent folding is the wrong way round too: `Ōkami` keys to
`kami`, so a distinct page `Kami` is dropped in its favour (that one at least is named in provenance).
Exposure: `t5.py` finds 0 entries with an empty key among 282,853 in data/records (3,872 non-ASCII names, all
with Latin letters), which is consistent with either "no such title on these wikis" or "all dropped here"; I
cannot tell which. This is Hard Rule 0's shape (a smaller universe that looks complete). Suggested fix: reuse
`backfill._name_key` semantics and count `key == ""` titles as `no_text`-style drops instead of `continue`.

### F3. LOW (reproduced) - codewatch.py:660-675 an unreadable ledger reads as an empty one, so the restart budget resets and the write wipes every other job's history

Quote: `doc = _read_ledger()` (returns `{}` on any exception)

`t3.py` (ledger redirected to a temp file): with `publish` at 4 restarts in the hour, `_claim_restart_slot`
returns `(False, 4)`. After truncating the file to `{"publish": [1, 2` it returns `(True, 0)`, and the file
afterwards holds only `publish`; `foreman`'s entry is gone. A torn file needs a non-atomic writer (all
writers here are atomic), but a transient read failure (`PermissionError` while a dashboard or scanner holds
the file on Windows) is the same path and is the ordinary Windows condition the module's own comments cite.
The result is a restart granted over budget, on the guard whose stated job is stopping restart storms.
Fail-open on unreadable input. Suggested fix: distinguish `FileNotFoundError` (empty) from any other error
(refuse the claim, escalate as CODEWATCH_LEDGER_DENIED).

### F4. LOW (reproduced synthetic; latent, 0 src files affected) - foreman.py:1698-1701 `_function_source` slices by `str.splitlines` but indexes by AST line numbers

Quote: `lines = src.splitlines(keepends=True)`

`splitlines` also breaks on `\u2028`, `\x85`, `\x1c-\x1e` (and form feed / vertical tab), which `ast` does not
count as line ends. `attempt_patch` then applies `lines[start:end] = [new]` to `f.readlines()`, which does
not split on them. With a `\u2028` inside a string above `f`, `t10.py` shows the model is sent
`'\ndef f():\n'` (a different slice) while the span replaced on disk is the whole of `f`. The model patches
text it was not given the real function of, `lines_changed` is computed against the wrong body, and the
whole-function replacement lands before `_checks_pass` runs. Currently no file in src/ has such a character
(`t10.py` scanned all of them: 0), so it is latent; `_BAD_CHARS` only guards foreman.py itself. Fix:
`io.StringIO(src).readlines()` for the slice, matching what the writer uses.

### F5. LOW (reproduced) - build_terminal.py:616-629 splices NAVTREE.json text into the page without parsing it, and exits 0

Quote: `data = f.read()` ... `html = TEMPLATE.replace("__DATA__", data)`

`t6.py` (DATA/OUT redirected): an empty NAVTREE writes `const DATA = ;`, a torn one writes
`const DATA = {"roots": ["0"], "nodes": {"0": {"na;`, garbage writes `const DATA = \u003chtml>oops;`; every
run prints `wrote ...` and returns 0, replacing the previous good `output/registry_terminal.html` with a page
that throws at load. Upstream NAVTREE writes are atomic, so this is latent, but the build has no check that
can fail: the only validation between the file and the published page is none. Fix: `json.loads(data)` and
check `roots`/`nodes` before writing; return 1 otherwise (the denied-write path already returns 1).

### F6. LOW - burgs.py:106-129 `burg_count` docstring says n = P_1/P_min, but the condition factors move n off that line, so "thriving" worlds fabricate a floor-pinned tail

Quote: `n = P_1 / P_min` (docstring) vs `return max(3, int(n * factor))` with `"thriving": 1.15`

`rank_population` floors at `HAMLET_FLOOR`, so every rank past P_1/40 comes back as exactly 40 people
whatever the rule says. `t13.py`, medieval: thriving p1=38,400, n=1,104, the rule ends at rank 960, and 144
burgs (13%) sit at exactly 40 where `int(p1/k) < 40`; ruined and wartorn undershoot the rule instead (n=27 vs
rule end 90; n=288 vs 360). `burgs_for`'s own comment calls this exact behaviour (ranks past `n`
"FABRICATING" floor-valued rows) the reason `limit` may only narrow, yet `burg_count` itself does it for
4,311 of 15,025 worlds (thriving; `WS.build_all()` counts). navtree reads `burg_count` as `nb`. Either the
factor is a deliberate condition effect (then the docstring's "consequence of the law rather than a second
parameter" is untrue) or it should not exceed 1.0 on the count. Modelled estimate, so LOW; filed because the
docstring is what a volume would quote.

### F7. LOW (reproduced; carries b16 Q4) - tempus.py:107-114 an unknown shelf name is answered as "no shared furniture"

`t9.py`: `apparent_lag_years('Call of Duty Zombies', 'Not A Real Shelf')` and `('zzz','yyy')` both return
`note: 'no shared furniture; relation is mediated or absent'`, identical to a real no-path case, so a typo or a
renamed shelf reads as a physical finding. Placeholder or ruled? (Still no production consumer of the
`None` distinction.)

### F8. LOW - backfill.py:213 a title whose name key is empty is "missing" on every run and re-added each time

Quote: `missing = [t for t in names if not _name_key(t) or _name_key(t) not in have]`

`have` is built with `- {""}`, and an added entry with an empty key cannot enter it, so a category member
named only with punctuation/symbols (no alphanumeric) is appended again on every backfill of that source. Rare
by construction; the new NFKD key fixed the CJK case that motivated it. Fix: dedupe those on the exact
(case-folded) name instead of the key.

### F9. LOW - pipeline.py:2860 (outside batch, caused by tells.py) doctrine count went stale

Quote: `138 machine-writing tells; Rule 7 is generated from the list`. `python src/tells.py` now prints 60 + 42 +
41 + 15 = 158 (2026-09-29 additions). CLAUDE.md's own lesson about counts in doctrine applies. Suggest "every
machine-writing tell" with no number.

### F10. LOW (code-evident, not run) - foreman.py:383 `triage_swallowed` files its archive under a minute-resolution key

Quote: `prev[time.strftime("%Y-%m-%d %H:%M")] = d`

Two archives in the same minute (two foremen, which main() allows by design, or a hand-run beside the daemon)
overwrite each other: the first snapshot's counts are gone from the archive after the ledger was cleared into
it. Also a plain read/clear race: counts `health.flush` adds between the ledger read (:335) and the clear
(:405) are erased. Fix: include seconds and a pid, or merge counts into an existing key.

### F11. LOW (code-evident) - catalogue_web.py:725-726 an empty `--only` term matches every source

`wanted = [n.strip().lower() ...]`, `any(w in r["name"].lower() for w in wanted)`: `--only "Bleach,"` gives
`w == ""`, and `"" in name` is True, so the run widens to the whole selection. Foreman's fragments are never
empty (guarded at foreman.py:1112), so this only bites a hand-run; drop empty terms.

## Questions (possible deliberate design)

1. foreman.py:1113 fragment uniqueness is checked against `gap` (short sources) only, and catalogue_web's
   `--only` is a substring match over the selection after `--shortfall 1`, which is the same set, so today the
   two agree. If catalogue_web's selection ever gains a filter foreman does not (it already has `in_scope`,
   added sweep67), a fragment can name a source foreman did not count. Today: 0 short sources, 8 out-of-scope
   rows, none short (`t12.py`), so no live effect.
2. codewatch.py:660 restart ledger, and foreman.py `attempt_patch`: prior questions 2-4 above still open.
3. tempus.py:119-156 comments disagree with each other: the header at :144 says every public symbol but
   `concordance_now` is read by "the battery or the pipeline", while three of them (:119, :131, :254, :297) say
   their only callers are test harnesses. Both may be true (battery = test harness); worth one line saying so.

## Cleared (traced, no defect)

- foreman.py: everything the sweep67 "cleared" list names, re-traced against current source (clear_learned_caps
  json predicate, reprove_pool did-honesty, adopt_hosts regex, `_restartable`/`_restart_horizon` shared derivation,
  `_python_processes` fail-closed, `_io_moving`, `_retire_stall_order`, `_catalogue_batch` rotation and rate,
  `restart_ollama` stamp fail-closed and gated did=True, `_ollama_generates`, `lines_changed`, `regex_touched`,
  `_contracts_pass` shape grading, `_checks_pass` numeric FAILED read and rc gate, `round_once` `.always`
  continuation, `owner_queue` uncapped and pid/thread scratch, `main` per-round halt). Apart from F1, F4, F10.
- codewatch.py: `_py_tree`/`fingerprint`/`quiet_seconds` None-is-not-unchanged, `stale()` two clocks and stamp
  corroboration, `runs_script` flag stepping, `twins`/`claim_singleton` self-exclusion, `stamp` retry and
  escalation (string "MANAGER" is accepted by `escalation.escalate`, BY_NAME), `_take_locked` denied-write refusal,
  `_ledger_lock` PermissionError arm, `_poll_pid_alive`, `exit_if_stale` budget vs ledger-denied split,
  `exit_if_paused` roster. Apart from F3.
- catalogue_web.py: composite/single flow, uncapped ranking (`top=None`), `_singular` rules, `save_roll` via
  `roll.update_rows`, `write_record_catalogue` gating and the post-merge `entry_count` (the merge extends
  `rec["entries"]` in place, so the roll count is the merged one), exit code, halt check on the writing path only.
- backfill.py: `roster()` uncapped, `RosterIncomplete`, `lead()` marked cuts, size-rank key, `--cap` opt-in with
  pre-cap `absent`, write gating, per-source containment and rc, halt only on the writing path.
- tells.py: all patterns compile without control characters; `_anchor` and the import guard; span suppression;
  `prompt_in_sync` CRLF fold and three-valued verdict; live prompt in sync (True, 3,041 chars).
- tempus.py: `is_present_at`, `contemporaneous`, `rung_description_length`/`band_resolution` (LADDER and BAND_EDGES
  keys identical, 11 bands, ceiling branch), `prescience_horizon_bits` positive-lead guard, `loop_report`.
- burgs.py: halt guard, `limit` narrowing, `class_histogram` via one `rank_population`, parameters-not-rosters write,
  `--write` denied-rename exit code. Apart from F6.
- build_terminal.py: `esc()` sinks, marked `trimmed()` cuts (full text in tooltip and panel), roster scroll not
  slice, `<` neutralisation, atomic write with denial in the exit code. NAVTREE has every field the JS reads (734
  nodes, none lacking `k`, no world lacking `d`). Apart from F5.
