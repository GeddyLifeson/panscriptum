# SWEEP 38 — AUDIT, batch 11

Agent: `sweep38-batch11`. Eight modules, 4,447 lines, all read in full. Audit pass only; nothing
under `src/` was edited. Reproductions were run from
`…/scratchpad/sweep38/batch11/repro{,2,3,4}.py` against the live tree with
`C:/Users/imarl/miniconda3/python.exe` and `PYTHONIOENCODING=utf-8`.

---

## overnight.py (1,365 lines) — READ IN FULL — 3 findings

### 1. `_proc_lines` / `running`: a probe that could not look answers "nothing is running" (MAJOR)
`overnight.py:104-127`, consumed at `:130-195`.

```
if now - _PROCS["at"] > ttl:
    try:
        _PROCS["out"] = subprocess.run([...powershell...]).stdout
        _PROCS["at"] = now
    except Exception:
        silence.note("overnight.py:proc-lines")
    return _PROCS["out"]
```
and `running()` opens with `if not out: return False`.

Two ways to get an empty listing without anything being wrong with the process table:
the PowerShell/CIM spawn raises (swallowed), or it returns cleanly with empty stdout and a
nonzero rc that nothing reads. Either way every job in the kit reads as DOWN.

Reproduced (repro.py section C/D), with `subprocess.run` patched to raise inside the module:

```
_proc_lines() -> ''
running('overnight.py')          -> False
running('dashboard.py')          -> False
running('literally_anything.py') -> False
autostart.supervisor_alive()     -> False      # not None
```
and again with a probe that succeeds and returns `stdout=""`, `returncode=1`:
`running('overnight.py') -> False`.

Everything that enforces ONE OF EACH reads this sensor: `main()`'s twin-supervisor guard
(`:1034`), `run()` (`:442`), `start()` (`:500`), the keeper thread (`:1063`), and
`_guarded_popen`'s "authoritative" second check (`:322`) — the spawn lock serialises the
decision but not the blindness. `autostart.supervisor_alive()` was given a tri-state precisely
so "could not tell" would not start a supervisor, and it is defeated here because it wraps
`bool(ON.running(...))` around a sensor that has no way to say "I don't know".

### 2. `ledger_report(top=8)` truncates a ranked diagnostic (MINOR, Hard Rule 0)
`overnight.py:650-669`. Header says `top {len(rows)}` beside `sum(d.values())`, the total
occurrence count — never the number of classes. Measured now: **47 distinct swallowed-failure
classes, 2,197 occurrences; 39 classes are never named anywhere in the night's log.** The same
cap was removed twice from this same file with written rulings (`did[:5]` at `:594-607`,
`[:top]` at `:638-645`) and survived in the function whose entire product is a ranked list.

### 3. The one blocking preflight condition is two unpinned literals (MINOR)
`overnight.py:853`: `blocking = "control characters in source" in out and "FAIL  control" in out`.
The label lives at `health.py:805` (`CHECKS[0][0]`), the `  FAIL  {label}` format at
`health.py:840`. Neither is pinned. `allsweep._HALT_REFUSAL`, the structurally identical
cross-module string, IS pinned (`verify_math.py:5252`) with a comment saying the two must not
drift silently. Also noted: the first conjunct is redundant (the label also appears on the
`ok    …` line), so the whole halt rests on the second; and `n = out.count("FAIL")` counts
substring occurrences rather than failing checks, which is a third quantity again from
`health.preflight`'s own `problems`.

### Read and found sound
`name_rc` (incl. the unsigned→signed NTSTATUS fold and rc=17), `_cmd_is_running`'s
interpreter+script+args test, `_in_this_tree`'s deliberate fail-open, `_guarded_popen`'s
banner-under-the-lock, `_manager_stopped`'s fail-closed both-spellings gate,
`coverage_snapshot`'s rc-and-mtime double check, `preflight`'s did-not-complete arm,
`safety_drill`'s `rc not in (0,1)` arm, `write_status`'s build-then-`replace_retry`, the
`busy`/`manager-stopped` idle accounting and the halted-not-broken branch. `STANDING` /
`ALL_JOBS` are a single roster with no partial copies.

---

## allsweep.py (768 lines) — READ IN FULL — 2 findings

### 4. The LINT tier scores CLEAN when pyflakes does not run (MAJOR)
`allsweep.py:575-599`. The "tier is BLIND" line is appended only from `except Exception`, and a
pyflakes that is absent or that errors does not raise — it exits nonzero with empty stdout.
`lr.returncode` is never read.

Reproduced (repro.py section A), the exact call shape with an uninstalled module:
```
rc            = 1
stdout empty? = True
stderr        = ['…python.exe: No module named pyflakes_not_installed']
lint_bad      = []
```
`main()` then prints `no undefined names in any module` and adds 0 to `bad`. The file's own
comment at `:704-709` claims this hole is closed ("being blind scored as clean"); it is closed
for the exception path only. Note that a blanket `rc != 0` is the wrong repair — pyflakes exits
1 as its normal "I found something" code (confirmed: rc=0 on a clean file, section B). The
correct shape already exists in this repo at `overnight.preflight`, `:867`, against
`health.py`'s identical `return 1 if n else 0` contract.

### 5. `reconcile()` joins six names and stores the truncated string (MINOR, Hard Rule 0)
`allsweep.py:344`, `:348`, `:352`, `:391`, and the `len(examples) < 6` guard at `:450`. Unlike
`art["bad"][:25]` at `:638-642`, there is no "and N more" and **the full list is not preserved
in `ALLSWEEP.json` either** — the truncated `detail` string is what is stored, so the names
past six exist nowhere. `main():666` then clips `detail` to 70 characters on the console.
Live now: `catalogued sources with no host` count=8, detail names 7, one source never named.

### Read and found sound
`Verifier`'s attribute-carried `rc_means` with the two-element unpack preserved, `run_verifier`'s
published `failed` grade and its fail-closed default, `check_import`'s halt-refusal and
SystemExit-without-traceback arms, `_row_is_fault`'s fail-closed keyless row, `estate_faults`,
`modules()`'s recursive walk, the `landed`-counts-as-a-fault term, and the honest "reconcile is
ungraded" note. `NEVER_RUN` is read by nothing — confirmed by grep — which is exactly what its
own comment says, so it is documentation-as-data, not a defect.

---

## identity.py (499 lines) — READ IN FULL — 2 findings

### 6. `DESIGNATORS.json` never refreshes, and staleness is silent (MAJOR)
`identity.py:219-248` (`load`) and `:251-257` (`continuities`). `load()`'s fast path serves
whatever is on disk with no TTL, no comparison against the corpus it is derived from, and no
staleness banner. Only a hand-run `identity.py --refresh` moves it, and nothing schedules one
(the `allsweep` row at `allsweep.py:170` runs `identity.py` with no `--refresh`).

Reproduced (repro3.py) against the live tree:
```
DESIGNATORS.json mtime : 2026-08-22 12:16:39   (178.8 hours old)
feats/ host dirs       : 142
keys in DESIGNATORS.json: 93
dirs mined since the cache was written: 51   (16,963 cache files)

dir 'bloons_fandom_com': 270 titles, 29 parenthetical
   continuities a FRESH mine would recognise: 3 -> ['BATTD', 'BTD6', 'BTDB Mobile']
   identity.continuities() answers today    : {}
```
`identify()` therefore returns `continuity=None` for every title on those 51 hosts, and
`chain.harvest` (`chain.py:269`) files each feat sentence with `continuity: None`, so
`ID.node(name, None)` (`chain.py:468`) collapses every branch onto one bare node — the merge
this module's own docstring calls the unrecoverable direction of the error, feeding
Bradley-Terry directly. Related second face of the same fault: `mine()` over an absent or empty
feats root returns `{}` (verified) and `load()` writes and then serves that as a positive
"no continuities" forever.

### 7. `continuities()` derives the host key by hand instead of via `cachekey.host_dir` (MINOR)
`identity.py:254`: `key = host.replace(".", "_").replace("-", "_")`, while `mine()` keys the
inventory on the actual directory names, which `cachekey.host_dir` produced
(`[^A-Za-z0-9]+ -> "_"`, capped at 40 chars). For six hosts on the current roll the two never
agree, so continuity lookup cannot succeed however fresh the cache is (repro.py section G):

| host | identity's key | actual dir |
|---|---|---|
| `pages:A Plethora of Paladins` | unchanged (`:` and spaces kept) | `pages_A_Plethora_of_Paladins` |
| `doc:arcanum-worlds-odyssey-of-the-dragonlords` | `doc:arcanum_worlds_…lords` | `doc_arcanum_worlds_odyssey_of_the_dragon` (40-char cap) |
| `pages:Guildmasters' Guide to Ravnica` | unchanged | `pages_Guildmasters_Guide_to_Ravnica` |
| `pages:KibblesTasty (techno-psionic line)` | `pages:KibblesTasty (techno_psionic line)` | `pages_KibblesTasty_techno_psionic_line_` |
| `pages:all Creeper World` | unchanged | `pages_all_Creeper_World` |
| `pages:the Sex Worker background` | unchanged | `pages_the_Sex_Worker_background` |

`cachekey.py` exists to be the one spelling of this path component and its docstring names four
sites; this is a fifth it did not catch.

### Read and found sound
`split`, `_is_continuity`'s three tests incl. the `n == 1` branching case, `mine`'s
shared-bearer signature, `epoch_of`'s `ProbeUnavailable` / `strict=` split and its
cite-by-symbol discipline, the `EPOCH_REQUIRED` block's move above the `__main__` guard, and
the write-denied report in `load()`.

---

## autostart.py (384 lines) — READ IN FULL — 1 finding

### 8. `install()` writes the Startup launcher non-atomically and does not verify it (MINOR)
`autostart.py:109-114` — plain truncating `open(VBS, "w")`, then `return VBS, "installed"` with
no read-back. `_vbs_body`'s own docstring says "A launcher that never launches is the worst kind
of automation: it looks installed", and a partial write leaves precisely that: a `.vbs` Windows
fails silently at every logon while `--status` (`:358`) prints "installed" because it only tests
`os.path.exists`. Every other shared-state write in this tree goes through
`silence.write_json` / `replace_retry`. Same order: `_log` (`:73-83`) does not
`os.makedirs(LOGDIR)` the way `overnight.log` does, so on a tree without `state/` the watchdog's
only voice is silently mute.

### Read and found sound
`supervisor_alive`'s tri-state (defeated from below — see finding 1, not autostart's fault),
`watch`'s `alive is None` refusal and hourly-budgeted starts, the `is False` test in `--install`,
`_twin_watchdog`'s delegation to `codewatch.twins` plus retry-and-say-so fail-open, the
deliberate `stale()`-not-`exit_if_stale()` reasoning, `start_supervisor`'s handle close in
`finally`, and `--status` reading `ON.ALL_JOBS` rather than a hand-kept subset.

---

## custodes.py (642 lines) — READ IN FULL — nothing found
Verified live: `dof_coverage() -> {'degrees_of_freedom': 10, 'custodes': 10, 'manned': 10,
'unmanned': [], 'one_to_one': True}`; `ATTESTATION_QUALITY` is genuinely derived from
`assay.ATTESTATION_FLOOR` (not a second copy); `assay.assay` does accept the `weights=` kwarg
`_custos_reading` passes, and the second (weighted) call cannot newly return `decimal=None`
because `assay`'s two None branches key on `worksheet` and on the score/weight key overlap,
neither of which the reweighting changes — so `idx + base["decimal"]` cannot raise.
`_transit_widening`'s fourth slot, the attendance block hoisted above the `len(readings) < 2`
return, and Threnody's `evidence_sensitivity=0.0` all check out against their comments.
`covers_every_reading` is a tautology, and says so at `:542-550` with the reasoning and a
NEXT_STEPS pointer — recorded as a question below, not filed.

## grounding.py (334 lines) — READ IN FULL — nothing found
The Hard Rule 0 repairs are real: `classify_text(top=None)` returns the whole field,
`classify_source` refuses a numeric `cap` loudly, the confidence denominator is the full field,
and `main()`'s contested list is uncapped and sorted most-contested-first. The `--write` path
gates on `silence.write_json`'s verdict and returns 1 on a denial. One nuance raised as a
question below.

## tuning.py (272 lines) — READ IN FULL — nothing found
Verified live: `state/cascade_scratch.db` really does carry `usage(ts REAL, outcome TEXT)`, the
`ts` values are float epoch seconds as the query assumes, and `cloud_success_rate()` returns
`(0.0329, 304)` — i.e. the CLOUD_MIN_SUCCESS floor is doing live work right now, not sitting
inert. `_CACHE` carries `buckets` alongside the verdict so `profile()`'s worker count and the
label come from one reading; `workers(0)` correctly returns 0. `PROFILES["cloud"]["workers"]=12`
is always overridden by `profile()` and `PROFILES` has no reader outside this module, but the
comment directly above it says so.

## cachekey.py (183 lines) — READ IN FULL — nothing found
`load()`'s ownership check, `write_path()`'s disambiguation branch, the N-way-safe
exact-name digest suffix, and `provenance_ok`'s three-outcome contract all match their
docstrings. `HOST_CAP`/`NAME_CAP` are filename caps retained deliberately with read-time
verification as the documented mechanism. Only cosmetic note: `text_digest` re-imports
`hashlib` locally at `:137` although the module already imports it at `:42` — harmless, not
filed.

---

## Questions, not findings

* **`grounding.classify_source` scans the synthesis blob unconditionally** (`:217-218`), outside
  the origin-entry filter, while the docstring at `:205-209` says "a source with no
  origin-bearing entry comes back UNGROUNDED by the honest route: no origin account is attested
  because none was written down". A source with `origin_entries == 0` whose synthesis rationale
  carries cosmogonic vocabulary can therefore be classified. Measured over all 210 records:
  **zero such sources today**, so this is latent either way. Two readings: the synthesis
  rationale IS a legitimate origin account and belongs in the scan (in which case the docstring
  sentence needs qualifying), or the targeting should apply to it too. Filed as a question at
  OWNER.
* **`custodes.convene`'s `covers_every_reading`** is true by construction and the code says so.
  Left as-is deliberately, with the genuinely-informative variant (did the 1.96σ band alone
  cover, or did the widening have to fire) named in NEXT_STEPS. Recording that this sweep read
  it and agrees it is a stated invariant, not a check.
* **`identity.main()`'s `top[:6]`** (`:489-490`) caps a per-host continuity display but does
  print `+N more`, and `--host` gives the full list. Honest, and inside the letter of the sweep
  brief's "no `[:N]` without and-N-more" — but grounding.py:299-304 refused a smaller cap on a
  smaller diagnostic. Not filed; noting the inconsistency for whoever rules on the house
  standard.

---

## Coverage
All eight modules in brief11.json read in full: `overnight.py`, `allsweep.py`, `custodes.py`,
`identity.py`, `autostart.py`, `grounding.py`, `tuning.py`, `cachekey.py`. None skipped.
