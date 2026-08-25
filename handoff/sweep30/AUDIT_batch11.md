# Sweep 30 — Batch 11 Audit: `src/assay.py`, `src/generate.py`, `src/rosetta.py`, `src/escalation.py`, `src/hosts.py`, `src/profile.py`, `src/ledger.py`

Auditor: batch11 (read-only, static). All 7 files read top to bottom in full (868 + 497 +
416 + 289 + 253 + 201 + 136 = 2,660 lines), no sampling. No committed secrets, API keys,
tokens, or credentials found anywhere in the batch — grepped for
`api_key|secret|password|token|BEGIN (RSA|OPENSSH|PGP)|AKIA...|xox[baprs]-|sk_live_|ghp_...`;
the two hits in `generate.py` are the ordinary-English word "token"/"tokens" in prose
comments, not credentials.

**`generate.py` was never executed** (prose gate audited statically only, per instructions).
**`escalation.py`'s `raise`/`clear` machinery was exercised read-only, with `HALT_FILE`
monkeypatched to a scratch directory** — see the incident note under escalation.py below;
it is disclosed in full because one of those test calls had an unintended side effect on
real repo state, which was found and corrected before this report was written.

---

## OPERATIONAL INCIDENT (disclosed up front)

While reproducing the "can a halt be lost" question for `escalation.py`, I called
`escalation.escalate(OWNER, ...)` with `HALT_FILE`/`LOG`/`SRC_LOGS` monkeypatched to a
scratch directory, deliberately pointing the halt-file *parent directory* at a blocking
file so the write would fail (to test the failure path — see finding escalation-1 below).
`escalate()` also calls `health.record(...)`, and `health.py`'s `LEDGER_PATH` is **not**
parameterised — it always points at the real `state/failures.json`. My triggered failure
path called `silence.note("escalation.py:halt-write")`, which arms `atexit.register(health.flush)`,
and `health.flush()` ran at process exit and wrote two new keys into the real
`state/failures.json`:

```
"escalation:OWNER:TEST_CODE:simulated disk failure while raising a halt": 1
"silent:escalation.py:halt-write:FileExistsError": 1
```

Both were caught immediately after (diffing the file against its pre-test content) and
removed via the same read-modify-atomic-replace pattern `health.flush()` itself uses
(`silence.replace_retry`), verified the two keys are gone and no other content changed.
No other repo file was touched by any test in this audit. Lesson for future audits of
`escalation.py`: `health.py`'s `LEDGER_PATH`/`SAMPLES_PATH` also need monkeypatching, not
just `escalation.HALT_FILE`/`LOG`/`SRC_LOGS`, before calling anything that reaches
`health.record()`. All subsequent reproductions in this report against `escalation.py`
used only the pure-read functions (`_read_halt_raw`, `status`, `assert_clear`) with a
scratch `HALT_FILE`, which have no side effects.

---

## `src/assay.py` (868 lines)

### Clean note
The file is unusually well-defended for a module of this history: a `_BAD_CHARS` guard
against the project's recurring "regex escape eaten by a shell heredoc" corruption,
`_check_scores()` refusing out-of-range axis scores, and `_check_constants()` running
**at import** to refuse a broken sigma table before any number is ever printed. The
disputed `_SCALE` calibration bug described in this batch's brief is **already fixed in
the current source** (see finding 1 — REFUTED against current source, confirmed working).

### 1. `_SCALE` halving bug — ALREADY FIXED, REPRODUCED AS CORRECT (INFO, not a defect)
`assay.py:334-399`. The brief's open item describes `_SCALE` as discarding the
charter-calibrated sigma (0.06 vs. the charter's 0.12). Reading the current source, this
is the *history* the file's own comments narrate — and the code has already been fixed
(dated 2026-08-25, today) to anchor `_SCALE` on the charter's own Witnessed calibration
point (`_ANCHOR_SIGMA = 3.2003`) rather than on the widest grade. Reproduced live:
```
_SCALE = 0.7843872549019607
SIGMA_BY_ATTESTATION = {'Instrumented': 2.1178, 'Witnessed': 3.2003, 'Transcribed': 4.1573,
                         'Reconstructed': 5.4907, 'Disputed': 6.6673}
calibration_report() -> {'interval': 0.12, 'want_interval': 0.12, 'decimal': 0.52,
                          'want_decimal': 0.52, 'holds': True, ...}
```
`calibration_report()` re-derives the charter's published Kenshiro interval (±0.12) exactly
through the live code, not by asserting a stored constant. **No action needed — flagging
so the sweep doesn't re-open a closed item.**

### 2. `axis_score()` returns a FLAT 9.9 for every positive input at the top band (HIGH, REPRODUCED)
`assay.py:211-229`. For `band == "M10"` (the last rung), `i + 1 >= len(LADDER)` is always
true, so the function returns the literal constant `9.9` for **any** `x > 0`, regardless
of magnitude — a feat one joule over the M10 floor and a feat 200 orders of magnitude
above it score identically:
```
axis_score(1e-10, 'M10', 'ruin')  -> 9.9
axis_score(1e200, 'M10', 'ruin')  -> 9.9
```
Compare `tempus.band_resolution()` (`src/tempus.py:182-210`), which handles the exact
same top-of-ladder edge case *correctly and with a comment explaining why*: "M10 has no
band above it, so it inherits the M9→M10 width" — it computes a real interpolation window
using `BAND_EDGES[LADDER[i-1]]` to `BAND_EDGES[band]` instead of collapsing to a constant.
`axis_score()` should do the analogous thing (interpolate against the M9→M10 width, or at
minimum clamp within that window rather than returning a fixed literal). As written, every
M10-band entity's Ruin/Reach/Celerity/Sustain/Continuity axis scores are meaningless — the
Instrument (`instrument()`, which reads these same axis scores) and any Assay composite
built from a scored M10 axis silently launders every M10 entity's real feat magnitude into
the same number. `magnitude.py:244` calls `A.axis_score(x, anchor, axis)` with a
data-supplied `anchor`, so M10 is a reachable, not merely theoretical, input.
**Suggested fix**: mirror `tempus.band_resolution()`'s top-of-ladder handling — use the
M9→M10 window to interpolate/clamp instead of returning a bare `9.9`.

### 3. `interval_from_hands()` is dead code, and `custodes._ATT_BASE` hand-copied its numbers instead of the live table (MEDIUM, REPRODUCED)
`assay.py:819-860`. Repo-wide grep for callers:
```
grep -rn "interval_from_hands(" --include=*.py . | grep -v "def interval_from_hands"
   (no output)
```
Zero callers anywhere in the tree — confirmed independently, matching what several prior
sweeps (`handoff/sweep22` through `sweep29`) already found. The function is fully dead.
Separately, `src/custodes.py:228-229` defines
`_ATT_BASE = {"Witnessed": 0.10, "Instrumented": 0.08, "Transcribed": 0.20, "Reconstructed": 0.40, "Disputed": 0.55}`
— an **exact copy** of the `floor` dict hardcoded inside the dead `interval_from_hands()`
(`assay.py:841-842`), even though `custodes.py`'s own comment two lines above claims this
table is "DERIVED from assay()'s own attestation table rather than restated" — it is not;
it restates numbers that live nowhere except inside dead code, and both copies are
numerically unrelated to the module's actual live table, `SIGMA_BY_ATTESTATION`. This is a
comment-contradicts-code finding on top of the dead-code finding. Out of this batch's file
list but flagged for cross-reference since the duplicate lives in `assay.py`.
**Suggested fix**: either delete `interval_from_hands()` (and its now-orphaned `HANDS` dict
context) as truly unused, or wire `custodes._ATT_BASE` to actually derive from
`SIGMA_BY_ATTESTATION` as its own comment claims it already does.

### 4. `_check_scores()` uses `is NONE` (identity) while the rest of the module uses `== NONE` (equality) for the same sentinel (MEDIUM, REPRODUCED)
`assay.py:444` (`if v is NONE or v in (INAPPLICABLE, UNESTIMABLE) or v is None:`) vs.
`assay.py:620` (`nil = [k for k in W if scores.get(k) == NONE]`) inside `assay()` itself.
`NONE = "none"` is a plain string (`assay.py:188`), and Python does not guarantee two
equal-but-independently-constructed strings share identity outside of compile-time literal
interning:
```
v = json.loads('"none"')
v is assay.NONE   -> False
v == assay.NONE   -> True
```
If a `scores` dict were ever built from a value that round-tripped through JSON (a saved
worksheet, a cached score) rather than referencing the module's own `assay.NONE` object
directly, `_check_scores()`'s `is NONE` branch would **not** recognise it as the NONE
sentinel, fall through to the numeric-type check, and raise `AssayIntegrityError` for a
value the rest of the module (`nil = [...]` at line 620, using `==`) would have handled
correctly. Currently the one known caller, `magnitude.py:348`, builds scores via a dict
lookup that returns the actual `A.NONE` object (`{"none": A.NONE, ...}.get(st, A.UNESTIMABLE)`),
so identity happens to hold today — this is a **latent** inconsistency, not a live failure,
but it is a real bug waiting on any future caller that deserialises scores. Given the
project's own stated philosophy (raise loud rather than clamp on bad input), this
particular failure mode is at least fail-closed (raises rather than silently mis-scoring)
— it would reject a legitimate reading rather than accept a bad one, which is the safer
of the two possible directions to be wrong in, but it is still a correctness bug.
**Suggested fix**: change `_check_scores()`'s `v is NONE` to `v == NONE` for consistency
with the rest of the file.

---

## `src/ledger.py` (136 lines)

### Clean note
`JOULES_PER_STANDARD` is imported from `physics.MATERIAL` rather than restated (avoids a
second silently-drifting copy of a shared constant) — good practice, matches the project's
own stated anti-pattern warning in its own docstring.

### 5. `assay_to_standards()` degenerates completely at the top band — `ruin_score` has zero effect (HIGH, REPRODUCED)
`ledger.py:127-136`, specifically line 132:
```python
i = LADDER.index(magnitude_band)
lo = BAND_EDGES[magnitude_band]["ruin"]
hi = BAND_EDGES[LADDER[min(i + 1, len(LADDER) - 1)]]["ruin"]
```
At `magnitude_band == "M10"`, `i == 10 == len(LADDER) - 1`, so
`min(i + 1, len(LADDER) - 1) == 10` — the same index as `i` itself — making `hi == lo`.
The log-interpolation on the next line then collapses to a constant regardless of
`ruin_score`:
```
assay_to_standards('M10', ruin_score=0.0) -> {'joules': 9.999999999999922e+98, ...}
assay_to_standards('M10', ruin_score=5.0) -> {'joules': 9.999999999999922e+98, ...}
assay_to_standards('M10', ruin_score=9.9) -> {'joules': 9.999999999999922e+98, ...}
all equal: True
```
By contrast, at M9 the same call genuinely varies across three orders of magnitude between
`ruin_score=0.0` and `ruin_score=9.9`. **This is the exact same top-of-ladder edge case as
`axis_score()`'s M10 bug above (finding 2), handled wrong in a different way**, and the
codebase already contains the *correct* pattern for it right next door:
`tempus.band_resolution()` (`src/tempus.py:206-209`) explicitly special-cases
`i + 1 >= len(LADDER)` by reusing the **previous** band's width (`BAND_EDGES[LADDER[i-1]]`
to `BAND_EDGES[band]`) instead of clamping the upper index back onto itself. `ledger.py`'s
`min(i + 1, len(LADDER) - 1)` clamp is the wrong direction — it should extend the window
backward like `tempus.py` does, not collapse it forward. Every price quoted for an M10-band
entity's destructive capacity is therefore identical no matter how strong or weak its
actual Ruin reading is, silently pricing the top rung of the Ladder as a flat number.
**Suggested fix**: port `tempus.band_resolution()`'s top-of-ladder handling —
`lo, hi = BAND_EDGES[LADDER[i-1]]["ruin"], BAND_EDGES[band]["ruin"]` when `i` is the last
index — into `assay_to_standards()`.

---

## `src/rosetta.py` (416 lines)

### Clean note
`numeric_rows()`'s row-scoped wikitable parsing (splitting on `|-` boundaries before
pairing links to numbers) is a real, well-documented fix for a genuine prior bug (pairing
Gecko Moria's name with Blackbeard's bounty one row down); the `_NOT_A_NAME` filter and
the "first number after the name, never the largest" column-order rule are both
specifically justified against measured failures in the comments, and check out on
inspection. `--mine` and `--refine` both write shared state exclusively through
`silence.write_json`, correctly following the two-writer contract.

### 6. `--check` compares only the fractional decimal, discarding which Magnitude band an entity is in (HIGH, REPRODUCED)
`rosetta.py:402-404`:
```python
assays = {k: v["result"]["decimal"] + P.__dict__.get("_x", 0)
          for k, v in json.load(open(path, encoding="utf-8")).items()
          if v.get("result") and v["result"].get("decimal") is not None}
```
`P` is `import pipeline as P` (`rosetta.py:44`). `pipeline.py` has no module-level
attribute named `_x` anywhere:
```
'_x' in pipeline.__dict__   -> False
pipeline.__dict__.get('_x', 0)  -> 0
```
So `P.__dict__.get("_x", 0)` is unconditionally `0` for every call, and the expression
reduces to `v["result"]["decimal"]` alone — the 0.00–0.99 fractional part of the Moth
Number, with **no band offset added**. Compare `assay()`'s own definition of a comparable
scalar value (`assay.py:623`): `value = LADDER.index(anchor) + composite / 10.0` — the
band index is load-bearing; without it, an M0.99 entity (decimal 0.99, essentially the
weakest possible reading) compares as *numerically greater* than an M9.05 entity (decimal
0.05, one of the strongest), because only the decimal survives. The entire purpose of
`rosetta.py --check` — validating the Assay's cross-franchise ordering against each
franchise's own published, canonical power scale via Spearman rank correlation — is
defeated by this: the correlation is computed between the native scale's real ordering and
essentially noise (a band-blind fractional residual), yet it prints plausible-looking
`rho` values and `DISAGREES` flags that nobody has any reason to distrust on sight. This
was very likely meant to add the band index (`LADDER.index(v["result"]["magnitude"])` or
similar) and never got wired up — `_x` reads as a placeholder variable name that was left
in.
**Suggested fix**: `assays[k] = A.LADDER.index(v["result"]["magnitude"]) + v["result"]["decimal"]`
(importing `assay` as `A`), matching `assay()`'s own scalar-value convention.

### 7. `_STAND` (JoJo Stand-stat parser) is compiled but never called — comment claims otherwise (MEDIUM, REPRODUCED)
`rosetta.py:104-105` defines `_STAND`, a regex meant to read Stand parameter blocks
("Power: A", "Speed: B", A–E letter grades) out of labelled context, specifically because
(per the comment at `rosetta.py:88-92`) bare single-letter grades match everywhere and an
earlier version graded 49 unrelated One-Punch Man entities from stray letters on the page.
The comment at line 91-92 says plainly: "Stand stats are read from their parameter block
instead (see `_STAND`)" — asserting this is the live mechanism used. It is not:
```
grep -n "_STAND\b" src/rosetta.py
   92:# from their parameter block instead (see _STAND).
   104:_STAND = re.compile(
grep -rn "_STAND\b" src/*.py
   (only the two lines above — no call site anywhere in the tree)
```
`_STAND` is referenced nowhere in `numeric_rows()`, `ordinal_rows()`, or `scales_for()` —
the three functions that actually mine a wiki page. The practical effect: JoJo's Bizarre
Adventure Stand statistics are never actually mined as a native scale at all (there is no
`ORDINAL_LADDERS` entry or numeric path that reaches `_STAND`), despite the file's own
comment describing this as solved. This is a comment-contradicts-code finding as much as a
dead-code finding.
**Suggested fix**: either wire `_STAND` into `scales_for()`/`numeric_rows()` as a third
parsing path for stat-block pages, or delete it and correct the comment.

---

## `src/escalation.py` (289 lines)

### Clean note (verified by direct reproduction, read-only)
The **fail-closed-on-corrupt-halt-file** property, explicitly called out as needing
verification in this batch's brief, is real and works correctly:
```
no halt file present         -> status() == (False, None)
HALT.json has unparseable content -> status() == (True, {'code': 'HALT_FILE_UNREADABLE', ...})
assert_clear() on a corrupt file  -> correctly raises SystemHalted
a standing (uncleared) halt       -> status() == (True, {...})
a cleared halt                    -> status() == (False, {...})
```
All four cases reproduced directly against `_read_halt_raw()`/`status()`/`assert_clear()`
with `HALT_FILE` pointed at a scratch directory (no writes involved — these are pure reads).

### 8. A halt-file write failure at the OWNER rung is silently swallowed — `escalate()` reports success and the halt never takes effect (HIGH, REPRODUCED)
`escalation.py:154-183` (`_raise_halt`). If the atomic write to `HALT_FILE` fails for any
reason (disk full, permission denied, an unwritable parent path), the exception is caught,
logged via `silence.note` and a `stderr` line, and **`_raise_halt` returns normally** — it
does not re-raise. Its caller, `escalate()` (`escalation.py:127-148`), does not check
`_raise_halt`'s outcome (it has none to check) and also returns normally. Reproduced with
`HALT_FILE`'s parent directory replaced by a blocking file so the write can never succeed:
```
escalate(OWNER, 'TEST_CODE', 'simulated disk failure while raising a halt', source='TEST')
  -> returned normally, no exception: {'code': 'TEST_CODE', ...}

assert_clear(who='next-caller')
  -> returned True   <-- the halt was never persisted; a subsequent caller sees "not halted"
                          and proceeds as if nothing happened
```
The module's own docstring states "THE HALT IS DELIBERATELY HARD TO CLEAR... It cannot be
cleared programmatically" and treats an *unreadable* halt file as fail-closed correctly
(finding above) — but a halt that was never *written* in the first place is
indistinguishable from no halt ever having been raised, and nothing here detects or
escalates that gap. The one mitigation present (`sys.stderr.write(...)`) only helps a human
who happens to be watching the terminal of the process that raised the halt at the moment
it failed; an unattended/overnight run (exactly the scenario Hard Rule -1 exists for) would
lose the halt with only a health-ledger counter (`silent:escalation.py:halt-write:...`)
as a trace, and nothing reads that counter as an escalation trigger in its own right.
**Suggested fix**: on a halt-file write failure, `_raise_halt`/`escalate` should not return
normally for an OWNER-level event — e.g. raise `SystemHalted` immediately in the calling
process as an in-memory fallback (so at least the process that detected the fault stops),
and/or retry against a fallback path, so "the halt file could not be written" is never
silently equivalent to "nothing happened."

### 9. `clear()` does not check whether its own write actually landed (LOW, REPRODUCED by code inspection)
`escalation.py:228-249`. `clear()` writes the tmp file and calls
`silence.replace_retry(tmp, HALT_FILE)` but never inspects the boolean it returns — it
unconditionally returns `True` and appends a `"HALT_CLEARED"` log entry even if the
replace failed and `HALT_FILE` on disk still holds the original, uncleared halt. This is
safe-side (the halt file itself, if the write failed, still says `cleared: false`, so
`assert_clear()` would still correctly block), but the function's return value and its own
audit-log entry would misreport a clear that did not actually take effect on disk — a
minor swallowed-failure finding, not a safety gap.
**Suggested fix**: `if not silence.replace_retry(tmp, HALT_FILE): return False` (and skip
the `_append_log` "HALT_CLEARED" call) before returning.

### 10. `clear()` has exactly one caller in `src/`: `drill.py`, testing that it *refuses* — verified this is deliberately excluded from the "no programmatic clear" scan, but the exclusion is a coverage gap (MEDIUM, REPRODUCED)
```
grep -rn "escalation.clear(\|ESC.clear(" src/*.py
   drill.py:390:        lambda: _refuses(lambda: ESC.clear(""), ValueError),
   drill.py:393:        lambda: _refuses(lambda: ESC.clear("ok"), ValueError), "")
```
Both calls pass invalid rulings (`""` and `"ok"`, both under the 12-character minimum) and
are wrapped in `_refuses(..., ValueError)` — i.e. `drill.py` is testing that `clear()`
correctly *rejects* bad input, never actually clearing anything. This matches the
docstring's claim about "no module in `src/` calls this [to succeed]." `drill.py`'s own
`_no_programmatic_clear()` net (`drill.py:476-485`) grep-scans every `.py` file in `src/`
for the literal strings `"escalation.clear("`/`"ESC.clear("`, but **explicitly excludes
both `escalation.py` and `drill.py` itself** from the scan
(`if not f.endswith(".py") or f in ("escalation.py", "drill.py"): continue`). This
exclusion is necessary for the drill file not to flag its own refusal-tests as a violation,
but it also means: if a future edit to `drill.py` ever added a *real* `ESC.clear(some_valid_ruling)`
call (not wrapped in a refusal-test), `_no_programmatic_clear()` would not detect it,
because `drill.py` is unconditionally skipped regardless of what it contains. Given
`drill.py` is run autonomously every cycle per the supervisor's own stated practice
(`CLAUDE.md`: "The supervisor runs this every cycle, before any stage starts"), this is a
real, if currently unexploited, gap in the one check that is supposed to guarantee "only a
person clears a halt." Not exploited today — verified the only two call sites in the
excluded file are refusal tests — but the check's coverage does not actually rule out a
future violation the way its name promises.
**Suggested fix**: have `_no_programmatic_clear()` still scan `drill.py`'s own source, but
only flag calls that are *not* wrapped in `_refuses(...)` (e.g. a stricter AST/regex check
for `ESC.clear(` not immediately preceded by `_refuses(lambda:`), rather than excluding the
whole file.

---

## `src/hosts.py` (253 lines)

### Clean note
`discover()`'s comment about not capping the entity roster used to score candidate hosts
("NO `[:40]`... a cap here scored every wiki on the same alphabetical first forty names")
checks out — the actual code (`names = list(by.get(source) or [])`) is genuinely uncapped.
`add()` correctly routes its write through `silence.write_json` (two-writer contract) and,
per its own comment, was deliberately changed from a fixed-tmp-name `os.replace` pattern to
avoid exactly the Norton-lock failure class this project has been bitten by before.

### 11. `add()`'s read-modify-write to `SOURCE_HOSTS.json` has an unguarded cross-process race window (MEDIUM, HYPOTHESIS — not live-tested against a second process)
`hosts.py:78-97`. Every call re-reads `EXTRA` fresh (`data = _load(EXTRA, {})`), mutates
the in-memory dict, and writes the whole dict back via `silence.write_json`. This narrows
the race window to a single call's duration rather than a whole `discover()` run, and the
underlying write itself is atomic — but there is no lock across the read-then-write pair,
so two processes calling `add()` for *different sources* within the same short window can
both read the same pre-update snapshot and each write back a dict containing only their own
addition, with the second write silently discarding the first's. `discover()`'s own
in-process concurrency (a 6-worker `ThreadPoolExecutor`) does not trigger this, because all
`add()` calls happen serially in the main thread as `ex.map` results are consumed — the
risk is specifically two *separate OS processes* (e.g. two `--discover --only=...` runs, or
a manual run overlapping a scheduled one) racing on the same file. Not reproduced against a
live second process in this read-only audit; flagged as a design gap consistent with the
project's known "records two-writer hazard" pattern noted elsewhere in this codebase.
**Suggested fix**: route through the same `silence.replace_retry`-with-merge pattern
`health.flush()` uses (read-merge-write inside the retry loop, or a file lock), rather than
a bare read-then-write.

### 12. `_load()` conflates "file absent" with "file corrupt" — both silently return the default (MEDIUM, REPRODUCED by code inspection)
`hosts.py:44-50`:
```python
def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        silence.note("hosts.py:load")
        return default
```
A bare `except Exception` catches both `FileNotFoundError` (a legitimate, expected state —
e.g. `SOURCE_HOSTS.json` not existing yet on a fresh checkout) and a genuinely corrupted
`WIKI_HOSTS.json`/`SOURCE_HOSTS.json` (malformed JSON, truncated write, wrong encoding) —
both return the same silent `default` (`{}`), with only a health-ledger counter as a trace.
If `WIKI_HOSTS.json` (the 194-source primary-host registry every other module in this
project trusts, per this file's own docstring) were ever corrupted, `primary_host()` would
return `None` for *every* source, and `hosts_for()`/`coverage()`/`discover()` would all
silently behave as if no source had ever been assigned a host — indistinguishable from "not
measured yet." This is exactly the failure shape Hard Rule -1 was written to eliminate
elsewhere in this codebase; `prose_gate.gate_open()` and `escalation._read_halt_raw()` both
correctly split this into two branches (`except FileNotFoundError: return <absent-state>`
vs. `except Exception: return <fail-closed-state>`), and `hosts.py` does not follow that
same pattern.
**Suggested fix**: split the `except` into `FileNotFoundError` (return `default` silently,
as today) vs. any other exception (raise, or at minimum return a distinguishable sentinel
that callers can treat as "unknown" rather than "empty").

---

## `src/profile.py` (201 lines)

### Clean note
`_b32`/`_unb32` (Crockford-style base32, `assay.py`-independent) are a correct bijective
round-trip on inspection and by spot-check. The `decode()` regex's strict `re.fullmatch`
means a malformed profile raises rather than half-decoding (confirmed also asserted by
`verify_math.py:818-819`).

### 13. TIEBREAK VERDICT — `profile.py:182-187`'s round-trip self-test: the disputed clause is a genuine, provable tautology; the check as a whole verifies only the address field, not "everything the profile encodes" (HIGH, REPRODUCED — settled empirically)

**The two prior readings were each partly right, and the disagreement is resolved by what
`decode()` actually does with the `"profile"` field it returns.**

`profile.py:182-187` (`main()`):
```python
bad = 0
for r in rows:
    d = decode(r["profile"])
    if d["address"] != r["address"] or d["profile"] != r["profile"]:
        bad += 1
```
`decode()`'s own body (`profile.py:94-112`) sets its return dict's `"profile"` field to the
literal input argument it was called with (`"profile": profile`, line 111) — it is never
reconstructed from the decoded fields, only echoed back verbatim. Proven directly:
```
d = decode(good_profile)
d["profile"] is good_profile   -> True     # same object, not just equal
d["profile"] == good_profile   -> True
```
Since `d = decode(r["profile"])` is always called with `r["profile"]` as its argument, the
clause `d["profile"] != r["profile"]` is comparing a string to itself by construction — it
is **mathematically incapable of ever being True**, for any input, valid or corrupted. This
is exactly the "checks that cannot fail" pattern this sweep is weighted to find hardest.

The other clause, `d["address"] != r["address"]`, is **not** a tautology — `r["address"]`
comes from `AS.assign(...)` in `build_all()`, independent of `decode()`, so this half of
the check is real and would catch corruption specific to the address-encoding path.

But the profile string encodes six things — address, genre, register, three feature axes,
band, and attestation count — and `build_all()`'s output rows (`profile.py:140-153`) retain
only `designation`, `profile`, and `address`. **There is no ground truth stored anywhere
for genre, register, features, band, or attestation**, so no comparison against them is
even possible in this loop, tautological or otherwise. Demonstrated by deliberately
corrupting only the genre segment of an otherwise-valid profile string (leaving the
address, feature, and band segments untouched) and running it through the exact condition
from `main()`:
```
good profile: PS-3nqk8n-myc-0000-32
corrupted (genre "my"->"sh", nothing else touched): PS-3nqk8n-shc-0000-32
decoded genre from corrupted profile: superhero   (intended: mythology)
decoded address matches original?    -> True
round-trip test flags this as bad?   -> False    <-- main()'s exact condition
```
The self-test does not notice — `bad` stays `0` even though the decoded genre is
objectively wrong. **This is not hypothetical**: `verify_math.py:806-816` runs the
identical pattern as part of the project's actual regression battery, and its label for the
second check is actively misleading about what it verifies:
```python
_rows = PR.build_all(limit=400)
check("every profile round-trips to its own address",
      all(PR.decode(r["profile"])["address"] == r["address"] for r in _rows), True, ...)
check("and to its own feature vector",
      all(PR.decode(r["profile"])["profile"] == r["profile"] for r in _rows), True)
```
The second `check()` is titled **"and to its own feature vector"** — but the assertion it
actually runs never touches genre, register, landform, climate, condition, tech, band, or
attestation; it re-asserts the same unconditional tautology as `main()`'s second clause.
The feature vector is never independently verified anywhere in this battery.

**VERDICT, empirically settled: the agent who called this tautological was substantively
correct in effect, though the mechanism has one nuance worth preserving.** The
`d["profile"] != r["profile"]` clause specifically is a pure, provable tautology (proven by
object identity, not just by argument) — it can never fire for any input. The
`d["address"] != r["address"]` clause is a real, non-tautological check, but it is the
*only* real content in a self-test whose own print banner claims "the string must
reconstruct the world exactly" and whose sibling assertion in `verify_math.py` is
mislabeled as testing "its own feature vector." Four of the profile's six encoded
components (genre, register, three feature axes, band+attestation) have no round-trip
verification anywhere in the codebase. The agent who called it "a real check" was right
only about the narrow address-comparison half, and wrong about what the check as a whole,
and as labelled, actually accomplishes.
**Suggested fix**: have `build_all()`'s rows retain the source `genre`/`register`/`features`/
`band`/`attested` values (or re-derive them independently, e.g. from `genres`/`tiers` +
`WS.build_all` output, the same way `r["address"]` is independently sourced from
`AS.assign`), and compare each of `d["genre"]`, `d["register"]`, `d["features"]`,
`d["band"]`, `d["attested_axes"]` against that independent ground truth. Delete or replace
the tautological `d["profile"] != r["profile"]` clause entirely — it contributes nothing.

### 14. `build_all()` conflates "no genres/tiers file yet" with "corrupted genres/tiers file" — same silent-default pattern as `hosts.py` finding 12 (MEDIUM, REPRODUCED by code inspection)
`profile.py:127-138`. Both `GENRES.json` and `TIERS.json` loads use a bare
`except Exception: silence.note(...); <default = {}>`. A corrupted `GENRES.json` would
silently degrade *every* world in the library to `genre="unclassified"`,
`register="classical"` rather than refusing — the same swallowed-failure shape as `hosts.py`
finding 12, and the same shape Hard Rule -1's `prose_gate.py`/`escalation.py` deliberately
avoid elsewhere in this codebase by distinguishing `FileNotFoundError` from other
exceptions.
**Suggested fix**: same as finding 12 — split absent-file (default silently) from
present-but-corrupt (raise or return a distinguishable sentinel).

---

## `src/generate.py` (497 lines)

### Clean note — the prose gate cannot be defeated by any path found in this file
This is the file this batch was most concerned about, and it holds up under adversarial
reading:

- **Single entry point.** `generate_job()`/`call_ollama()`/`build_prompt()` have zero
  importers anywhere else in the tree:
  ```
  grep -rn "generate_job|call_ollama|from generate import|import generate" src/*.py | grep -v "^src/generate.py"
     (no output)
  ```
  The only way any of this file's functions run is via `main()`, called from
  `if __name__ == "__main__"`. There is no second, alternate call path into the model.
- **Gate checked before anything else.** `main()`'s very first substantive action
  (`generate.py:347-354`) is `PG.assert_gate_open(cfg)`, wrapped in a `try/except
  PG.ProseRefused`, and it runs *before* the manifest is even loaded — even `--dry-run`
  (which never calls Ollama) is gated, which is stricter than it needs to be but is
  consistent with a fail-closed philosophy.
- **Fails closed on config trouble.** `load_config()` (`generate.py:40-42`) does a bare
  `yaml.safe_load` with no exception handling of its own — a missing or malformed
  `config.yaml` crashes the process before the gate check runs at all (crash = no
  generation, which is fail-closed by omission). `PG.gate_open()` itself (in
  `prose_gate.py`, imported by this file) explicitly catches read/parse failures and a
  non-dict result and refuses in both cases, and uses `is not True` (strict identity, not
  truthiness) against `prose_enabled` — so `"false"` (a truthy string, the exact trap this
  project has been bitten by before per `CLAUDE.md`'s Hard Rule -1 history) does not open
  it. Verified in the live config: `config.yaml:108` currently reads `prose_enabled: false`
  (a real YAML boolean, not a string) — the gate is presently closed, correctly.
- **No second, looser implementation found live.** The only other module that used to carry
  a second gate check, `overnight.py:_prose_enabled()` (`overnight.py:44-68`), now
  delegates to `prose_gate.gate_open()` directly rather than reimplementing the condition —
  its own docstring documents the exact defeat this closes (the old `bool(cfg.get(...))`
  reimplementation opened on `"false"`, `"no"`, `"1"`, etc.) and dates the fix 2026-08-25.
  Grepped every `prose_enabled` reference in `src/`; no other reimplementation exists today.
- **Evidence floor also fails closed.** `main()`'s `PG._coverage_rows()` call
  (`generate.py:380-387`) is wrapped so that an unreadable `COVERAGE.json` refuses
  *everything* ("REFUSING EVERYTHING: data/COVERAGE.json unreadable...") rather than
  proceeding with an empty evidence table.
- **Shared-state writes correctly route through `silence`.** `save_json()`
  (`generate.py:53-58`) is a thin wrapper over `silence.write_json`, used for both
  `catalog.json` and `failures.json` — consistent with the two-writer contract.

Two lower-severity observations, not defeats of the gate:

### 15. Stale `silence.note()` site label (LOW, REPRODUCED)
`generate.py:447`: `silence.note("generate.py:166")` sits inside the `except Exception as e:`
block that is currently at line ~446, not line 166 (line 166 is inside `_covered()`, an
unrelated function). This is purely a telemetry-grouping label in `health.py`'s ledger
(`silent:generate.py:166:<ExceptionType>`) — it has no functional effect, but it will
mislead anyone using the label to find the failure site by line number.
**Suggested fix**: update the label to the current line, or to a stable non-line-number tag.

### 16. `context_budget`/`prose_gate` layers are imported inline, per-call, rather than at module scope (INFO, not a defect)
`generate.py:132, 155, 240, 303, 314, 347` all do `import <module>` inside a function body
rather than at the top of the file. Functionally harmless (Python caches imports), and it
is consistent with how the rest of this codebase defers heavier imports — noted only
because it makes grepping this file's actual dependency surface slightly less obvious at a
glance; not worth changing.

---

## Summary table

| # | File | Finding | Severity | Status |
|---|------|---------|----------|--------|
| 1 | assay.py | `_SCALE` halving bug | INFO | already fixed, reproduced correct |
| 2 | assay.py | `axis_score()` flat 9.9 at M10 | HIGH | REPRODUCED |
| 3 | assay.py | `interval_from_hands()` dead + `custodes._ATT_BASE` copy | MEDIUM | REPRODUCED |
| 4 | assay.py | `_check_scores` uses `is NONE` not `== NONE` | MEDIUM | REPRODUCED (latent) |
| 5 | ledger.py | `assay_to_standards()` degenerates at M10 | HIGH | REPRODUCED |
| 6 | rosetta.py | `--check` uses dead `P._x`, band-blind | HIGH | REPRODUCED |
| 7 | rosetta.py | `_STAND` regex dead, JoJo Stands never mined | MEDIUM | REPRODUCED |
| 8 | escalation.py | halt-write failure silently swallowed | HIGH | REPRODUCED |
| 9 | escalation.py | `clear()` ignores write-failure return | LOW | REPRODUCED (safe-side) |
| 10 | escalation.py | `_no_programmatic_clear` excludes drill.py wholesale | MEDIUM | REPRODUCED (coverage gap) |
| 11 | hosts.py | `add()` cross-process race on SOURCE_HOSTS.json | MEDIUM | HYPOTHESIS |
| 12 | hosts.py | `_load()` conflates absent/corrupt | MEDIUM | REPRODUCED |
| 13 | profile.py | round-trip self-test tiebreak | HIGH | REPRODUCED — settled |
| 14 | profile.py | `build_all()` conflates absent/corrupt GENRES/TIERS | MEDIUM | REPRODUCED |
| 15 | generate.py | stale silence.note() line label | LOW | REPRODUCED |
| - | generate.py | prose gate itself | — | CLEAN, no defeat found |
