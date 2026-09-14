# Sweep 58 — batch 06 audit

Modules read in full (top to bottom, paged where large):

| module | lines |
|---|---|
| src/standards.py | 2467 |
| src/liveness.py | 1054 |
| src/identity.py | 752 |
| src/autostart.py | 613 |
| src/catalogue_codex.py | 511 |
| src/snapshot.py | 376 |
| src/profile.py | 327 |
| src/ledger.py | 220 |
| src/cachekey.py | 213 |

Open queue checked first via `workorders.open_orders()` (script run against the live
`state/workorders.json`) before any of the below was written, per the brief's method §1.

## src/standards.py (2467 lines)

Not in run #58's "rewritten this shift" list; the file is heavily self-documented with
its own history of found-and-fixed defects (green-by-absence, tautological empty-file
passes, caps on diagnostic fields, etc.). No new defect found beyond one still-open KNOWN.

- **KNOWN d9328fe1ee38** (STALL_STANDARD_WATCHES_THE_LOG_NOT_THE_WORK) — still accurate.
  The "every running job is advancing" standard (now at `standards.py` inside `check()`,
  the block building `stalled`/`watched`/`unmeasurable` from `LN.OWNER` logs, ~lines
  1669-1782) still measures advancement purely from `job_stamp(prev, size, now)` on the
  job's **log file size** — there is still no second witness against the job's own output
  tree (e.g. newest mtime under the directory a crawl writes into). The remedy the order
  proposes (a second witness, or an `unmeasurable` routing where no output tree is
  declared) has not been applied. Order should stay open.
- **KNOWN 7099a092abd3** partially bears on this file too: `standards.py`'s own
  `check()` is one of the battery-adjacent callers that the order's AST-scan excludes when
  counting "production" callers of `ledger.py`'s functions — consistent with what is
  written there; no new observation to add here (see ledger.py below for the primary
  finding).

Nothing else found. Checked: every `_s(...)` standard block for compare-and-swap shape
(`silence.write_json` / `roll.update_rows`-equivalent), fail-closed vs. green-by-absence
handling (`_dropped` routing), all `subprocess` spawns (`ollama_runner_up`'s `tasklist`,
the `Get-CimInstance` duplicates probe) for `CREATE_NO_WINDOW` (both present), and the
self-check (`every declared floor is measured`) for a stale citation — none found.

## src/liveness.py (1054 lines)

Extremely mature, self-auditing module (it exists specifically to catch tautologies /
dead code / phantom guards, and its own docstring catalogues several defects already
fixed in its own passes: the `seen`-always-truthy conditional at the old line ~549, the
receiver-blind `used` bag, the module-pass gap, etc.). Read the whole `scan()`,
`_credit_attrs`/`_scope_aliases`/`_self_attrs` scoping logic, and the newer
`reachability()` (gate-reachability-via-coverage) code end to end.

- All three `subprocess.run` calls inside `reachability()` (the `coverage --version`
  probe, the `coverage run`, and `coverage json`) pass `creationflags=_NO_WIN`. No
  console-window exposure.
- Nothing found. Checked the DEAD/DEAD_CLASS/TAUTOLOGY/PHANTOM passes' scoping rules
  (per-function alias maps, MRO-by-name walk, phantom's `defined` set covering
  `MatchAs`/`MatchStar`/`MatchMapping`/walrus-via-Store/lambda `arg` nodes) and found no
  gap beyond the ones the module's own docstring already declares open (the
  known/declared module-wide PHANTOM under-report, order 2e0ba4b02ec4).

## src/identity.py (752 lines)

- **KNOWN 5d0fa30e4b09**, item 7 — still accurate, unchanged. `continuities()`
  (`identity.py:470-479`) and the equivalent inline lookup in `main()` (`identity.py`
  around 706-710) both test `if inv.get(k):` when walking `_inv_keys(host)` candidates,
  rather than `if k in inv:` — so a host whose inventory is a real, mined, **empty**
  dict (`mine()`'s own docstring: "a visited directory gets a key even when it has no
  designators... An empty dict says 'mined, nothing found'") is treated the same as a
  key that is simply the wrong spelling, and lookup falls through to try the next
  candidate spelling instead of stopping at the correct, empty answer. Per the order:
  this only misattributes on a genuine key-spelling collision between two hosts (rare),
  and no live instance was found when it was filed; still a QUESTION, not a DEFECT, and
  no evidence of a live instance was found this pass either.

No other findings. Checked `mine()` for Hard Rule 0 (uses every title in every file
under a host directory, no sampling/cap), `_is_continuity()`'s branching/population math
(including the `n == 1` special case and the "more than half" majority for `n == 2`),
`load()`'s cache-staleness repair and its refusal to overwrite a populated inventory
with an empty mine, and `_inv_keys()` against `cachekey.host_dir()` for consistency
(confirmed consistent — see cachekey.py below).

## src/autostart.py (613 lines) — the live watchdog

Read specifically for spawn paths and halt-reading per the brief.

- **Spawn paths / console windows: clean.** The only `subprocess.Popen` in the file is
  `start_supervisor()`, which sets `flags = _NO_WIN | subprocess.DETACHED_PROCESS` on
  `os.name == "nt"` (`_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)` defined once
  at module top and reused). The `.vbs` launcher built by `_vbs_body()` runs
  `WScript.Shell.Run(cmd, 0, False)` — window style `0` — so the logon path is also
  windowless. No spawn site in this file is missing the flag.
- **Halt reading: correct and matches its own docstring.** `watch()`'s loop reads
  `escalation.status()` only when `alive is False` (`halted = None; if alive is False:
  try: import escalation as _ESC_WATCH; halted, _halt_rec = _ESC_WATCH.status() except:
  halted = None`), and `_start_decision(alive, starts, now, halted)` is a pure function
  that checks `halted is True` (return "halted", spending no budget) strictly before the
  `MAX_STARTS_PER_HOUR` budget check — matching the fix this file records for
  order 06041602990d (starts used to be spent on refused-by-halt attempts). An
  unreadable halt (`None`) falls through to the ordinary start path, which is the
  documented deliberate fail-open ("the supervisor asks the halt itself, first, and
  refuses on its own").
- **KNOWN 4c2101d54c10** (WATCHDOG_ABSENT) — still accurate, still open. The order's own
  text says the fix restored the watchdog for that incident but explicitly left
  unresolved "nothing detects a dead watchdog" (no Scheduled Task/service layer, no
  liveness check on `autostart.py --watch` itself from anything still alive when it
  dies). Confirmed: nothing in the current file adds such a layer — `_log`, `install`,
  `uninstall`, `supervisor_alive`, `_twin_watchdog`, `_start_decision`, and `watch` are
  unchanged in this respect from what the order describes. The three remedy shapes the
  order lists (self-liveness-check, a Scheduled Task that re-runs the Startup command on
  an interval, or a daily maintenance assertion) are all still absent.

No other findings.

## src/catalogue_codex.py (511 lines)

Nothing found. Every collision/truncation class the module tracks (section-title norm()
clashes, ambiguous substring section binding, ambiguous register descriptions,
(type,name) manifest duplicate drops, unmapped element types) is reported uncapped
before the write summary, matches Hard Rule 0. Write path is gated
(`pipeline.write_record_catalogue`'s return value is checked; a denied roll write via
`roll.update_rows` is surfaced and reaches the exit code via `return 1`). No subprocess
spawns in this file. No known order names this module.

## src/snapshot.py (376 lines)

Nothing found. Read `_rel()`'s containment check, `before()`'s all-or-nothing capture
with `allow_missing`, `_dir_matches()`'s byte-for-byte directory walk, `verify()`'s
temp-directory restore-and-compare, `_safe_join()`'s second containment check on
`restore()`, and `restore()`'s own missing-entry refusal. All match their documented
fixes (order ca3452eb9d49 path-escape fix, order da72c19bef09 nanosecond+pid id and
`write_json`-backed manifest, order e5116f51c82a directory-content verification, order
f4193095edff/9681220bad8f partial-capture and partial-restore refusals). One minor,
low-value observation not filed as a DEFECT: if `_rel()` raises partway through a
multi-path `before()` call (a later path resolves outside the repo after earlier paths
were already copied into `dest`), the partial `dest` directory is left on disk rather
than cleaned up — this does not compromise the safety property (the caller still sees
`SnapshotFailed` and the destructive step still does not proceed) and is disk hygiene
only, not filed as a QUESTION or DEFECT given no consequence could be demonstrated.

## src/profile.py (327 lines)

Nothing found. `encode()`/`decode()` round-trip logic, the B32 alphabet fix (32 symbols,
no `u`), the `_PROFILE_RE` alphabet-derived-from-`B32` fix, the per-axis range check in
`decode()` (raising a named `ValueError` instead of a bare `IndexError`/`ValueError` from
inside `_unb32`/`B32.index`), and `main()`'s round-trip check (`re_encoded != r["profile"]`,
not the old tautological `d["profile"] != r["profile"]`) are all present and correct as
documented. No known order names this module.

## src/ledger.py (220 lines)

- **KNOWN 7099a092abd3** (BATTERY_IS_THE_ONLY_CALLER_OF_THIRTEEN_PUBLIC_FUNCTIONS) — still
  accurate. Confirmed by direct read: `cross_rate`, `to_standards`, `from_standards` and
  `assay_to_standards` are exported, documented, arithmetically self-consistent, and
  (per the module's own docstring, which independently records this) have "no caller in
  the generation pipeline at all... the only import of it anywhere in the tree is that
  battery" (referring to `verify_math.py`). This matches order 7099a092abd3's count
  exactly for this module's four listed symbols. The module's docstring also documents a
  *related but distinct* ruling (order 3fb9fc6b9999, "HELD for a future phase") for the
  module as a whole, which is the deliberate-retention side of the same fact the
  liveness/battery-caller order is about.
- QUESTION (not filed as a DEFECT — no live instance demonstrated): `assay_to_standards()`
  checks `if magnitude_band not in BAND_EDGES: return None` and then unconditionally calls
  `LADDER.index(magnitude_band)`. If `BAND_EDGES` ever held a key absent from `LADDER`
  (both live in `assay.py`, outside this batch, so not verified against source), this
  would raise an uncaught `ValueError` instead of returning `None`. Given this function's
  only callers are the battery per the finding above, and `assay.py` was not read this
  batch, this is left as a QUESTION rather than a DEFECT.

## src/cachekey.py (213 lines)

Nothing found. `host_dir`/`name_stem`/`_suffix`/`natural_path`/`disambiguated_path`/
`candidate_paths`/`owns`/`load`/`write_path` all match the documented collision-repair
design (verify-on-read via the stored `entity`/`host` keys, disambiguate-on-write only
when the natural path is already owned by a different entity). Cross-checked against
`identity._inv_keys()`'s use of `cachekey.host_dir()` — consistent, no drift found.

## Coverage-stamp confirmation

`sweep_plan.record("run58", [...], batch=6)` called for exactly the 9 modules listed in
the table above (see the module's own final report for exit confirmation).
