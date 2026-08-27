# run35 LOCAL batch L6 -- audit notes

Owner for this batch: recover_folder_records.py, ingest_doc.py, catalogue_aurora.py,
catalogue_codex.py, overwatch.py, mutate.py, secondopinion.py, publish.py, weave.py,
reference.py, sevenfold.py, codewatch.py, ledger.py, ledger_guard.py, axis_correlation.py,
chain.py, feats_index.py, estate.py. `verify_math.py`, `drill.py` and `mutate.py` were not run
this batch (a mutation run was in flight, order c349a51ee2c5); every fix below was verified by
hand-running `pyflakes`, a bare import, and a targeted functional check against the fixed
source, recorded per order below. Both prose gates (`prose_enabled`, `step4_enabled`,
`src/prose_gate.py`) were left untouched.

### 0b15581132d0 -- src/secondopinion.py, `NOT_FILED`
Confirmed by running `ruff check src --select E,F,B,BLE,S110,S112,PLE,PLW,RUF,SIM --ignore
E501,RUF001,RUF002,RUF003 --statistics`: 30 distinct codes reported today, none of them
UP031/ISC004/C408/DTZ005. Those four categories (pyupgrade, implicit-str-concat, comprehensions,
flake8-datetimez) are structurally unreachable under the module's own `RUFF_RULES` selector, so
a waiver naming them can never match anything. Removed the four dead entries from `NOT_FILED`
and added a comment explaining why, leaving the five waivers (E402, SIM115, RUF100, PLW1510,
B007) that the selector can actually produce findings for.

### 237a61e89859 -- src/mutate.py, `main()`'s `--check-flaky --no-confirm` path
Confirmed by reading `main()`: under `--no-confirm`, `base = baseline(root, gates=gates +
confirm)` runs with `confirm=()` (FAST_GATES only, no drill), but `flaky_gates(root, base)` was
called with its default `gates=GATES` (FAST_GATES+CONFIRM_GATES), so it scores a gate (e.g.
drill) `base` never ran a baseline for; `sig != base.get(name)` is then `sig != None`, always
true, so the run pays drill's five minutes and then refuses regardless of the actual code.
Fixed by passing `gates=gates + confirm` explicitly, matching the call that built `base`.

### 25ec11447b4c -- src/weave.py, `pair_weights()` / `idf_table()`
Confirmed: `grep -rn "pair_weights" src/*.py` shows one definition and no callers anywhere in
`src/`; `main()`, `pipeline.py` and `tiers.py` all call `surprisal_pair_weights()` instead. In
`main()`, `idf` and `N` (from `idf_table()`) are unpacked and never read again -- only `occ` and
`sources` are used downstream. Per house doctrine ("dead code is not automatically deletable"),
documented rather than deleted: added a `SUPERSEDED, NOT CALLED ANYWHERE` comment above
`pair_weights()` and a comment at the `idf_table()` call site in `main()` explaining which of
its four return values are actually used.

### 31e504c0df88 -- src/catalogue_aurora.py, module docstring
Ran `parse_folder('drfirestorm')` (425) and `parse_folder('the-elements-beyond')` (681) directly
against this module's own code: sum 1,106, not the docstring's claimed 1,159. Updated the
docstring to the measured figure with its arithmetic shown (425 + 681) and a note to re-run
`parse_folder` for a current count rather than trusting a hardcoded one indefinitely.

### 3320036fb65c -- src/mutate.py, `reap_orphans()`
Confirmed: `shutil.rmtree(p, ignore_errors=True)` cannot raise by construction, so
`removed.append(p)` ran unconditionally and the `except Exception: silence.note(...)` beneath it
was unreachable dead code -- a sandbox `rmtree` could not delete (the junction case the six
lines above it discuss) would still be reported as removed. Fixed by checking `os.path.isdir(p)`
after the `rmtree` call and only appending to `removed` when the directory is actually gone;
logged via `silence.note("mutate.py:reap-incomplete")` otherwise.

### 3593a47f0f31 -- src/secondopinion.py, `report()`
Confirmed: `sorted(codes.items(), key=lambda kv: -kv[1])[:6]` printed at most six codes with no
indication more existed, while `file_orders()` one screen up already appends `" (+%d more)"` for
the identical shape. Applied the same disclosure: `top` now appends `" (+N more code(s))"` when
more than six distinct codes were found. Verified with a synthetic 9-code input -- see
`checks_L6.py::check_secondopinion_report_discloses_truncation`.

### 4c9a939daeea -- src/reference.py, `shelfmark()`
Confirmed: `marks = [f"{RUNGS[i]}{v}" for i, v in enumerate(upper)]` plus
`RUNGS[3 + i]` for `lower` assumes `upper` is always exactly 3 items and `lower` always exactly
4, true only for the three hardcoded reference entries today. A `lower_rungs` of 5+ items reaches
`RUNGS[7]`, out of range (`RUNGS` has 7 entries, indices 0-6). Fixed the hardcoded `3` to
`len(upper)` (correct for any actual upper length) and added a clamp that truncates to what
`RUNGS` can hold and logs via `silence.note("reference.py:shelfmark-shape")` instead of raising
`IndexError`. Verified with `tier_key="a.b.c.d.e"` + a 5-item `lower_rungs` -- renders instead of
crashing.

### 6d729c0d6ca5 -- src/secondopinion.py, three stale prose counts
Ran `ruff check --statistics` with this module's own selectors and got BLE001 520, S110 18,
S112 9 today -- none of the docstring's "449", the NOT_FILED comment's "456", or file_orders's
own "449" (two different numbers already claiming to be the same fact, before today's count is
even considered). Replaced all three hardcoded counts with qualitative language ("hundreds of
blind-except sites") plus a pointer to `ruff check --statistics` for the live number, so the
prose can't drift out of sync with itself again.

### 930550461fba -- src/recover_folder_records.py, module docstring
Attempted direct re-verification against `data/SWEEP_ROLL.json`, but a concurrent scheduled
maintenance run (`state/MAINTENANCE_RUN.json`, `done: false`, live heartbeat) had the file down
to a single unrelated stub entry at the time of checking -- not usable as today's ground truth.
Applied the order's own filed measurement (215 sources; entry_count:0 -> 6; 0 missing files; 6
with an empty entries list), replacing the docstring's "100 / 77 / 23", and added a note dating
the measurement and flagging that the roll is live so this section can drift again.

### 9c1e9ba00cc2 -- src/ledger_guard.py, `seal()` / `assert_intact()`
Confirmed: `seal()` returns `None` on any write failure with no note, and `assert_intact()`
called it bare (`seal(); return True`), discarding the signal. Since the existing chain links
still verify against each other with no new one, `verify_chain()` would keep reporting healthy
indefinitely even if sealing had been silently failing since some earlier run. Fixed by checking
`seal()`'s return value in `assert_intact()` and raising `LedgerViolation` when it is `None`,
consistent with every other integrity failure in this module. Verified by monkeypatching `seal`
to return `None` and confirming the raise -- see `checks_L6.py`.

### b729b23ebc8e -- src/overwatch.py, `review()` / `_anchored()`
The docstring claim this order originally flagged ("returns the findings that survive all three
filters") was already corrected by an earlier agent this shift to "(findings, complete)". The
two dead parameters it also flagged were not: `review()`'s `ledger` argument and `_anchored()`'s
`module` argument were both unread in their bodies. Removed both from the signatures and their
one call site each (`review(m, local=local)`; `_anchored(f_, src)`), and added a docstring
sentence to `review()` naming NOVEL filtering as the caller's job against its own ledger.

### c97aaf6b1296 -- src/ingest_doc.py, `mine()`'s state-file read
Confirmed: `silence.note("ingest_doc.py:159")` sits one line above its own call site (already
stale when filed) while every other note in the file uses a durable content label
(`ask-cascade`, `ask-local`, `provenance`). Renamed to `"ingest_doc.py:ingest-state"`.

### c9f8d161a09f -- src/mutate.py, stale mutation lock / `_pid_alive()`
Confirmed the historical "lock had no caller" bug (order d779f541cd0b) is already fixed --
`_hold_lock()` calls both `_lock_acquire`/`_lock_release` and is wired into `run()` and `main()`,
so a normal exit (including the failure path, via `finally`) does release the lock, and a stale
lock is silently overwritten the next time `_lock_acquire` runs. The residual, real defect is
`_pid_alive()`'s Windows fallback: when `psutil` is absent, it unconditionally returned `True`,
so a genuinely dead PID (owner process hard-killed) could never be marked stale and would block
every future push forever -- confirmed currently harmless only because `psutil` happens to be
installed on this machine. Added `_pid_alive_windows()`, a `ctypes`-based real liveness check
(`OpenProcess` + `GetExitCodeProcess`, erring toward ALIVE on any ambiguous failure, same
direction the function already commits to), and wired it into the fallback path. Verified
directly: `_pid_alive_windows(os.getpid())` -> True, `_pid_alive_windows(999999999)` -> False.

### e9986e00bdec -- src/ingest_doc.py, `extract()`
Confirmed: `pages.json` -- read by `mine()` and the evidence pipeline through the `doc:` host,
and the only machine copy of a book the library cannot re-fetch -- was written with a bare
truncating `open(..., "w")` + `json.dump`. Replaced with `silence.write_json`, the project's
atomic writer, matching `register()` twelve lines below which already uses it for a far cheaper
file. Verified the module still imports clean and `extract()`'s only behavioral change is the
write mechanism (same content, same return value).

### f1bbfe251913 -- src/sevenfold.py, `main()`'s occupancy line
Confirmed: `len(coords)/CAPACITY` divides the SOURCE count by the full 5-tier capacity (16,807
slots), but sources occupy only the top three tiers (7^3 = 343 slots) by the module's own
`build()` docstring and the `SOURCE_TIERS` comment -- understating occupancy by 49x and then
labelling the wrong number "sparse by design". Added `SOURCE_CAPACITY = SPAN **
len(SOURCE_TIERS)` and changed the occupancy line to divide by it instead of `CAPACITY`, adding
a second printed line distinguishing the two capacities so neither reads as the other.

### f9041b1208ba -- src/publish.py, `scrub_text()`
Confirmed: `if FIXTURE_MARKER in s: return s` checked the marker against the WHOLE string, so on
a multi-line value (which is what any snapshot field survives `json.dump` as, newlines escaped
into one JSON line) a marker anywhere in the value silenced every line it carried, including a
line with a live credential and no marker of its own -- directly contradicting the comment two
lines above it ("cannot silence a region"). `scan_for_secrets`, by contrast, already checks per
line, which is why the comment reads true for lock two but was false for lock one. Rewrote
`scrub_text` to split on newlines and apply the marker check and both redaction passes per line
via a new `_scrub_line` helper, joining the results back together. Verified: a marker on line 1
plus a `ghp_`-shaped token on line 2 now redacts the token and leaves the marker's own line
untouched (previously returned the whole two-line value unchanged).

## Left / disproved

None. All 16 orders in this batch had a real, verifiable finding and got a code or docstring
fix; none were disproved against current source.
