# sweep45 — batch 12 audit

Read in full, no sampling: `src/overnight.py` (1,724), `src/silence.py` (1,010),
`src/rosetta.py` (730), `src/autostart.py` (543), `src/anchors.py` (457),
`src/cosmography.py` (335), `src/resync_roll.py` (311), `src/propagation.py` (235).
5,345 lines, 100% of each. Read-and-report only; no source file was edited, and no battery
tool (`drill.py`, `verify_math.py`, `allsweep.py`, `publish.py`, `mutate.py`) was run. Every
grep hit was opened and confirmed to be a CODE line before anything was filed — several
apparent defects turned out to be comments recording a repair that has already landed (see
"Already fixed" below).

---

## 1. `silence.py`'s write path — the priority-one question

The specific failure modes the coordinator asked about were checked one by one against source
and **none of them is present**:

* **Can `write_json` land a partial file?** Not by any in-process route. The temp is fully
  written and CLOSED inside `with open(tmp, "w")` before `replace_retry` is called
  (`silence.py:728-729`); a `json.dump` that raises part-way discards the temp and re-raises
  (`:730-731`); `os.replace` is an atomic directory-entry swap. The one residual exposure is
  crash/power-loss durability — filed below as `698963577852`, MINOR, and explicitly not a
  race.
* **Can it report success for a refused replace?** No. `True` is returned in exactly three
  places, each immediately after a successful `os.replace`: `replace_retry:660`,
  `replace_if_unchanged:604`, and `write_json:749` which returns `replace_retry`'s own
  verdict unchanged. There is no path to a truthy return without a completed rename.
* **Does the "NEVER RAISES for any OSError" promise hold?** Yes, verified branch by branch.
  `replace_retry` catches `PermissionError` first and bare `OSError` second (`:656-670`), so
  `EXDEV`, `ENOSPC`, a vanished temp and a directory-shaped target are all covered; `note()`
  is total (`:767-799`, everything inside one `try` ending in `except Exception: pass`);
  `os.path.basename` and `time.sleep` cannot raise. The fall-through `return False` at `:673`
  is reachable only from the last-attempt `PermissionError` arm, which notes first.
* **Is a temp left behind?** `write_json` discards on both the dump-error and denied-replace
  paths (`:730`, `:749`). `replace_if_unchanged` deliberately does not — that is the caller's
  temp — and the two callers inside this batch's blast radius (`overnight.write_status`) do
  clean up. `autostart.install()` does **not**, and that is filed (`521b551b790b`).
* **Does a retry retry something it should not?** No. `replace_if_unchanged` re-digests the
  target immediately before every one of its `os.replace` attempts (`:590-602`), so the
  compare and the swap stay adjacent across the backoff; permanent `OSError`s are reported
  rather than retried in both helpers.

What *is* wrong in the write path is smaller and is filed:

| id | severity | where | fault |
|---|---|---|---|
| `895ed2946027` | MINOR | `silence.py:593`, `:598` | Both of `replace_if_unchanged`'s refusals record the **same** ledger class `stale-write-refused`. One is a genuine fault (target unreadable — a writer that will never land); the other is ordinary CAS contention. The file argues against exactly this collapse twice, at `:616-621` and `:666-669`. |
| `698963577852` | MINOR | `silence.py:727-732` | No `fsync` before the rename, so `write_json`'s unqualified "ATOMICALLY" holds against readers and writers but not against a crash. Narrow, real, and worth either fixing or saying in the docstring. Same gap in `overnight.write_status:1211-1215`. |
| `83122ea1003f` | MINOR | `silence.py:500-504` | `_close_quietly` is a bare `except OSError: pass` with no `note()` and — unlike its neighbour `_unlock` — no stated reason. A failed close is a leaked descriptor in daemons that call `append_line` per model call. `_discard_tmp`, the other cleanup helper in the same module, does note. |

Also noted, not filed: `replace_retry`'s docstring and `replace_if_unchanged`'s `OSError`
comment both say a permanent fault "will not pass in 1.5 seconds", but the backoff with
`attempts=5` sleeps 0.3 + 0.6 + 0.9 + 1.2 = **3.0 s**. The reasoning is unaffected; the number
is stale by 2x in two places.

---

## 2. Filed this batch (worst first)

1. **`895ed2946027`** LOCAL/MINOR — `silence.py:593,598` — two CAS faults under one ledger name.
2. **`698963577852`** LOCAL/MINOR — `silence.py:727-732` — `write_json` has no `fsync`; the
   atomicity promise is unqualified.
3. **`83122ea1003f`** LOCAL/MINOR — `silence.py:500-504` — `_close_quietly` swallows without a
   mark or a reason.
4. **`521b551b790b`** LOCAL/MINOR — `autostart.py:175-185` — `install()` leaks its scratch file
   into the **Startup folder** on both failure paths (write error and denied replace). Nothing
   in the tree cleans it up; `silence.write_json` and `overnight.write_status` both do this
   correctly, and the second cites the first. Temp name also carries pid only, no thread ident.
5. **`7d08eb10c1a7`** LOCAL/MINOR — `overnight.py:1442-1447` with `:1276-1280` — the per-lap
   `codewatch.exit_if_stale` check added this shift sits under `except NameError: pass`. Two
   faults: the sticky "codewatch never imported" case fires every lap for the life of a
   days-long supervisor and records nothing anywhere; and the arm also swallows a `NameError`
   raised *inside* `exit_if_stale`, silently disabling the interlock — not hypothetical in a
   tree where `foreman --patch` edits `src/`. `autostart.py:405-407,416` solves the identical
   problem correctly by binding `codewatch = None` and guarding on the value.
6. **`a130056c11dc`** LOCAL/MINOR — `resync_roll.py:116-122` — a record file that parses as an
   object but declares no `source` is dropped with no note, no count and no output line: the
   last unguarded skip in a loop whose other three skips (`:91-99`, `:112-115`, `:141-144`)
   were all closed for this exact reason and are all named in the closing caveat.

---

## 3. Corroborated — already open, not refiled

* `b29076f9e999` — `autostart.watch()`'s `said_stale_at` is only stamped inside `if is_stale:`,
  so the hourly throttle never engages while the tree is current. **Still live** at `:416-419`.
* `7ae8965922b1` — `overnight._in_this_tree`'s two `return False` handlers record nothing.
  **Still live** at `:270-278`.
* `6a3e4238042d` — `run()` maps `_guarded_popen`'s blind-probe `None` onto `"already-running"`,
  defeating the `probe-blind` status it builds three lines earlier. **Still live** at `:540-541`.
  (Impact is confined to the status string: both values land in `busy`.)
* `d4c18b4b8743`, `e266d67b9d2c` — `resync_roll.py:242,250` still cut source names at 44 chars.
* `377b69ad3c0e` — **partly** live: the `--refine` cuts (`[:12]`, `[:44]`) are gone, but
  `--probe`'s `[:6]` and `n[:34]` (`rosetta.py:546,548`) and `--check`'s `r['scale'][:38]`
  (`:701,708`) remain.
* `e8f59f0800fd`, `d773ad5756ab`, `67a45b2dcaf8` — `propagation.py` name cuts, bare `main()`,
  and the unreachable trailing `return 0`. All still live.
* `18d0fedabf13`, `bd673ceaaf31` — `anchors.py` computes `CU.convene(...)` and
  `R.measure_bit_value(...)`, prints them, and grades neither; the five `CLAIMS` lambdas take
  `col` and none uses it. Still live at `:190-191`, `:208`, `:337-370`.
* `55787199eba7`, `adaeaa7ad639`, `c22c8b1f426c`, `cdfeccbfbab0` — the whole of
  `cosmography.py`'s open surface (unused declared constants; `POCKET`/`MINOR` always raising).
  Re-verified: `census('POCKET')` and `census('MINOR')` still cannot return.
* `78d6aa8eb434`, `78f2bebed995`, `eca7cb1d2d8f`, `68459d3e739b` — `rosetta.py`'s `--probe`
  blindness, `refine()`'s premature `kept`/`dropped` accounting, and the fetch-reported-as-
  search conflation at `:569-570`. All still live.

## 4. Already fixed — do NOT re-file (the comment/code trap)

Four open orders match text in the tree that is now a **comment describing the repair**:

* `0bd115293333` — `uninstall()` now catches `OSError` and returns a third verdict
  (`autostart.py:210-216`).
* `0c4649dd9f78` — the twin probe no longer sleeps on the final attempt
  (`autostart.py:332-333`).
* `2f8ebf12e5f2` — `--status`'s job-roster loop now handles the tri-state
  (`autostart.py:533-536`).
* `e41c9c2e4839` — the idle-limit halt check now fails **closed** and notes
  (`overnight.py:1697-1705`).
* `52a73082c56b` — `assays_by_host` now splits only when `|` is present (`rosetta.py:410`).
* `64ffa3ba30df` — `resync_roll` now snapshots `have_on_disk` before the repair loop (`:64`).

## 5. Deliberate design — examined and not filed

* `cosmography.validate`'s `abs(sum(KARDASHEV_MIX.values()) - 1.0) > 1e-6` is a check over an
  immutable module constant and cannot fire in production. It is the REVERSIBLE property this
  module declares in its own docstring — a guard for the person who edits the constant — so it
  is design, not a dead check.
* `anchors.py`'s ceiling claim tests `str(v).startswith("30")` rather than `v == 30`. Since
  `assay.instrument` computes `min(30, ...)`, 30 is the only value ≤ 30 whose string starts
  with "30", so the test is correct today. Fragile, not wrong.
* `silence.note()` called from `append_line:454` and from `replace_if_unchanged`'s refusals
  runs outside any `except`, so `sys.exc_info()` is empty and the class name is all the ledger
  gets. For `append_line` this is deliberate and documented (`:420-430`, the `why` carried by
  hand); for the CAS refusals it is the argument inside filing `895ed2946027`.
* `silence._unlock`'s `except Exception: pass` is silent **with** a stated reason (the OS drops
  the lock at close). Correct as it stands.
* `overnight.running()`'s `except ValueError: continue` on a non-integer pid field carries an
  explicit `silence-exempt` marker and the measurement (35,806 ledger entries in two hours)
  that justifies it.
