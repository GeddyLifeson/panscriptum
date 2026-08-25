# AUDIT — BATCH 15 (sweep run31)

Modules audited (every line read, in `src/`):
`overwatch.py` (715 lines) · `build_terminal.py` (579 lines) · `allsweep.py` (469 lines) ·
`estate.py` (338 lines) · `tuning.py` (263 lines) · `chord_field.py` (203 lines) ·
`scale_theories.py` (148 lines)

**Total lines read: 2,715**

`chord_field.py` and `scale_theories.py` are physics-reference/data modules (constants,
formulas, docstrings). No correctness, cap, or contract issues found in either — formulas
checked against their stated derivations (Kerr self-focusing, Landauer bound, recoil momentum,
kinetic energy) and all matched their docstrings. Not discussed further below.

---

## FINDING 1 — `allsweep.py:98-119` `check_import()` reclassifies a real detected corruption
as a clean import, because it only looks for the string `"Traceback"` in stderr

**Claim:** any module that fails to import because it deliberately calls `raise SystemExit(msg)`
at module load time — which is exactly what the corruption guard present in `tuning.py:52-53`,
`overwatch.py:68-70`, `allsweep.py:59-61`, and `estate.py:43-45` does (`"a regex escape was eaten
in transit"`) — gets reported by `allsweep`'s IMPORT tier as **`ok=True, "no CLI (imported
cleanly)"`**, i.e. a pass.

**Why it's wrong:**
```python
tail = (r.stderr or "").strip().splitlines()
err = tail[-1][:150] if tail else f"rc={r.returncode}"
if "Traceback" not in (r.stderr or ""):
    ok, err = True, "no CLI (imported cleanly)"
```
This assumes any nonzero exit without the literal word "Traceback" in stderr means "the module
has no `argparse`, that's not a fault." But an uncaught `SystemExit` (raised with a string
message, e.g. every `_BAD_CHARS` guard in this project) never prints a traceback — CPython
special-cases `SystemExit` in its top-level exception handling and just prints the message.
Verified directly:
```
$ python -c "raise SystemExit('boom: a real corruption message')"
returncode 1
STDOUT: ''
STDERR: 'boom: a real corruption message\n'
Traceback in stderr: False
```
So the exact self-check this project put in multiple files to catch "a regex escape was eaten
in transit" — the single most-repeated silent-corruption class named in this codebase's own
comments — is invisible to `allsweep`'s IMPORT tier. A module corrupted in exactly the way these
guards exist to catch would import-check as **clean**.

**Failure scenario:** any control-character corruption event in `tuning.py`, `overwatch.py`,
`allsweep.py` itself, or `estate.py` → `python <module>.py --help` exits 1 with the guard's
message on stderr, no "Traceback" present → `check_import` returns `ok=True` → `allsweep`'s
IMPORT tier prints "N/N import and parse their CLI cleanly," `broken_modules` stays empty, and
the run's exit code and `bad` count (line 455) do not reflect the corruption at all.

**Severity:** blocking. **Confidence:** VERIFIED (reproduced the underlying Python behavior
directly; the heuristic is read verbatim from the file).

---

## FINDING 2 — `estate.py` docstring says "every file, opened. No sampling anywhere"; the code
only opens `.json` and eight text extensions — everything else (including the exact `.db` file
`tuning.py` depends on) is merely stat'd for size

**Claim:** `inspect()` (lines 60-116) contradicts both its own module docstring (line 18: "every
file, opened. No sampling.") and `artifacts()`'s docstring (line 120: "Every file in the project,
opened and checked. No sampling anywhere.").

**Why it's wrong:** `inspect()` branches only on two cases —
```python
ext = os.path.splitext(path)[1].lower()
if ext == ".json":
    ...json.load(f)...
elif ext in TEXT_EXT:      # TEXT_EXT = (".py",".md",".txt",".yaml",".yml",".js",".html",".css")
    ...f.read(); ast.parse if .py...
```
Any file with any other extension only ever passes through `os.path.getsize(path)` at the top of
the function (line 64) — it is never `open()`ed for content at all, contradicting "opened" and
"No sampling anywhere." Binary and other-extension files (`.db`, `.sqlite`, images, fonts, `.csv`,
`.zip`, etc.) get a byte count and nothing else; a truncated or corrupted one is indistinguishable
from a healthy one to this checker.

**Concrete instance — verified on disk:** `tuning.cloud_success_rate()` (tuning.py:169-172) reads
`state/cascade_scratch.db` via `sqlite3.connect`, and that file exists:
```
$ find . -iname "*.db"
./state/cascade_scratch.db
```
`state/` is one of `estate.artifacts()`'s scanned roots (estate.py:122-123). If this database were
corrupted, `estate.py` — the module whose entire stated purpose is "a corrupt cache is
indistinguishable from a cache that is genuinely empty... It is the project's signature defect, at
rest, across its largest surface" (module docstring, lines 11-16) — would never notice, because
`.db` is neither `.json` nor in `TEXT_EXT`. Downstream, `tuning.cloud_success_rate()`'s bare
`except Exception: silence.note(...); return None, 0` (tuning.py:183-185) would swallow the
corruption too, feeding straight into the M19 sample-size problem in Finding 4 below.

**Severity:** major. **Confidence:** VERIFIED (code read directly; `.db` file's existence and
location confirmed on disk).

---

## FINDING 3 — `overwatch.py`: a module whose review is cut short by cloud-budget exhaustion is
still marked fully "seen," silently discarding coverage with no record it happened

**Claim:** `_ask()` (lines 348-380) can silently return `None` for a slice — meaning that slice
was never reviewed by any model, local or cloud — and `round_once()` (lines 639-667) then marks
the whole module "seen" at its current digest regardless.

**Why it's wrong:**
```python
# _ask(), lines 369-378
_LOCAL_BUSY[0] += 1
if _LOCAL_BUSY[0] > CLOUD_BUDGET:
    # THE WATCHER YIELDS. ...
    return None
```
`review()` (line 421-423) does `got = _ask(...)` then `for f_ in (got or {}).get("findings", [])`
— a `None` return yields zero findings, exactly as if the slice had been read and found clean.
Then in `round_once()`:
```python
# lines 647-648
d = _digest(os.path.join(SRC, m + ".py"))
led["seen"][m] = {"digest": d, "at": time.time()}
```
This runs unconditionally after `review()` returns, with no check for whether any slice was
actually skipped. `_LOCAL_BUSY[0]` is a **per-round, cross-module** counter (reset only at the top
of `round_once`, line 600) — so once one module's slices push it past `CLOUD_BUDGET` (=20), every
remaining slice of every remaining module in that same round's `todo` list also returns `None`,
each one contributing zero findings, and each one still gets `led["seen"][m]` written with a
fresh digest and a fresh (very recent) `at` timestamp.

**Failure scenario:** the local GPU is busy doing the corpus read (explicitly documented as "true
most of the time and false exactly when the pipeline is doing its own model work," lines 364-368
— i.e. a routine, expected condition, not a rare edge case). A round with `--modules 4` (the
production flag) picks up 4 modules; the first one or two burn through the 20-call cloud budget;
the rest get zero real review this round. Because `rotation()` (lines 504-521) decides "changed
vs. stale" purely from digest match against `led["seen"][m]["digest"]`, and that digest was just
recorded as matching current content, those under-reviewed modules are NOT flagged as "changed"
next round — they fall into the "stale" queue sorted oldest-`at`-first (line 520), and their `at`
is now the freshest in the whole ledger, so they go to the *back* of the queue. A module can be
skipped this way for an extended stretch while `WATCH.md` reports it as reviewed, with no trace
in the ledger that its coverage was partial.

**Severity:** blocking (it defeats the semantic-review half of the tool's stated purpose exactly
during the condition the module's own comments say is routine). **Confidence:** VERIFIED (code
read directly; the interaction between the two functions is unambiguous).

---

## FINDING 4 — `tuning.py:188-212` `regime()`: with a near-zero-size cloud success sample, the
"answering AND succeeding" gate collapses back to "answering alone" — contradicting its own
docstring, and reproducing the exact defect the file says it fixed (M19)

**Claim:** the docstring at lines 191-193 says `"'cloud' now means answering AND succeeding...
Reachability was never the question the callers of this function are asking."` The code does not
enforce that when the call sample is small.

**Why it's wrong:**
```python
judged = rate is not None and calls >= MIN_CALLS_TO_JUDGE        # MIN_CALLS_TO_JUDGE = 20
...
if n >= CLOUD_MIN_BUCKETS and (not judged or rate >= CLOUD_MIN_SUCCESS):
    r = "cloud"
```
`not judged` is `True` whenever fewer than 20 calls have landed in the last 15 minutes
(`cloud_success_rate(minutes=15)`, tuning.py:160). In that branch the success-rate half of the
`and` is bypassed entirely — the whole test degrades to `n >= CLOUD_MIN_BUCKETS`, i.e. reachability
alone, which is precisely the "different claim" the file's own comment (lines 68-76) says was
proven to cause "1,168 of 1,235 chunks... handed to a GPU that could not serve them and were thrown
away." This is a check that cannot fail for exactly the population flagged as risky
(`MIN_CALLS_TO_JUDGE`'s own comment, line 84: "Below this many recorded calls the rate is noise and
is not allowed to veto") — but "not allowed to veto" in practice means the gate opens by default
under sparse data, not that it stays cautious.

**The self-feeding loop (why the sample stays near-zero rather than filling in):** the 20-call
threshold is evaluated only against calls in the **last 15 minutes**
(`cloud_success_rate(minutes=15)`). The only source of rows in that window is the `usage` table,
which is populated by calls actually attempted under whatever regime was previously chosen. Once
`regime()` reads "local" or "starved" (because an earlier judged sample showed a bad success rate),
no more cloud calls are attempted, so no more `usage` rows accrue, so after 15 minutes the earlier
bad-rate evidence ages out of the window and `calls` drops back toward 0 — at which point
`judged` becomes `False` again and, buckets permitting, `regime()` flips back to "cloud" purely
on reachability, restarting the cycle. A near-zero-size sample can and does pin the regime, exactly
as flagged.

**Severity:** major (this is the file's own documented open bug, M19; confirmed present in the
current code with a specific mechanism for why the sample stays thin). **Confidence:** VERIFIED
for the "near-zero sample bypasses the success gate" mechanism (direct code read); the
oscillation/self-feeding dynamic across regime flips is HYPOTHESIS (well-supported by the code's
structure — `RECHECK_SECONDS=180` re-evaluates every 3 minutes against a 15-minute window fed only
by whichever regime was last active — but not observed against live telemetry in this read-only
audit).

---

## Minor / cosmetic findings

**5. `overwatch.py:504-521,636-637` `rotation()` / `round_once()` — possible starvation of
"stale" modules by chronically-changing ones, given production's `--modules 4`.**
`todo = (changed + stale)[:limit]` puts every digest-changed module ahead of every
long-unread one. Under normal operation this self-clears (a cold-start backlog of "never seen"
modules is itself "changed," and each gets promoted to "seen"/"stale" once read, so coverage
converges). But if `len(changed) >= limit` persists round after round (a handful of modules edited
faster than the review cadence), the rest of `src/` — dozens of other modules — could go
unreviewed indefinitely with no signal that this is happening, which is the same failure shape
Hard Rule 0 warns about (a report that looks complete while quietly excluding part of the
universe). Severity: minor/hypothetical — under this project's own steady-state (a mostly-stable
tree with occasional edits) it behaves as documented pacing, not a hard cap. Confidence:
HYPOTHESIS.

**6. `overwatch.py:572-573` `write_report()` truncates the human-readable findings list in
`WATCH.md` to the newest 40, though the full count and the full ledger (`OVERWATCH.json`) are
preserved.** `for f in sorted(open_f, ...)[:40]:` — borderline Hard-Rule-0 territory (an "entry
list" truncation) but distinguishable from the banned pattern because no data is dropped from the
ledger, only from the rendered digest; the accurate total (`len(open_f)`) is printed alongside.
Severity: minor. Confidence: VERIFIED the truncation exists; judgment call on whether it qualifies
as a violation.

**7. `allsweep.py:177,181,185,224,283-288` `reconcile()` caps example lists in `detail` strings to
6 items** (`orphan_hosts[:6]`, `no_host[:6]`, `missing[:6]`, `stale[:6]`, `examples` capped at 6 via
`if len(examples) < 6`) **while the accompanying count (`n`) is always the true, uncapped total.**
Same category as #6 — a display truncation with the real count preserved, not a silent universe
shrink. Severity: minor. Confidence: VERIFIED.

**8. `build_terminal.py:571-573` `main()` writes `output/registry_terminal.html` with a plain
`open(OUT, "w")` + `f.write(html)`, not through `silence.replace_retry` / `silence.write_json`
the way every other shared-output writer in this batch does (`overwatch.py:585-588`,
`allsweep.py:436`).** Not a two-writer race in the strict sense (this script is not documented as
having concurrent writers), but it is inconsistent with the project's own atomic-write convention
for anything under `output/`/`data/` that other processes may read while a write is in progress —
a reader (e.g. a browser loading the terminal, or `estate.terminal()`/`estate.artifacts()`) could
observe a truncated file mid-write. Severity: minor/cosmetic. Confidence: VERIFIED the write is
non-atomic; HYPOTHESIS that it is ever actually read concurrently.

**9. `overwatch.py:225,231` `_STATE_RANK` dict defines ranks for `"stale"` and `"confirmed"`
states, but no code path in this file ever sets `f["state"]` to either value** — the only states
ever assigned are `"open"` (line 654), `"closed"` (line 491), and `"retired"` (line 628). The
`verify_open()` "confirmed" verdict (line 495-497) only increments a `confirmed_n` counter and
leaves `state == "open"`, matching its own docstring ("confirmed stays open and says so") — so
this is intentional for `"confirmed"` but leaves the `_STATE_RANK` entries for `"stale"` and
`"confirmed"` as dead/unreachable code, which reads as if those are live lifecycle states when
they are not. Severity: cosmetic. Confidence: VERIFIED (grepped every `state` assignment in the
file).

---

## Summary by severity

- Blocking: 2 (Finding 1, Finding 3)
- Major: 2 (Finding 2, Finding 4)
- Minor: 4 (Findings 5, 6, 7, 8)
- Cosmetic: 1 (Finding 9)
