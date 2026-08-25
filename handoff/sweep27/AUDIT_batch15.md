# Batch 15 audit — run27

Modules read in full, every line, no sampling:
- src/assay.py (649 lines)
- src/derivation.py (558 lines)
- src/onomast.py (407 lines)
- src/address.py (290 lines)
- src/anchors.py (250 lines)
- src/coverage.py (191 lines)
- src/repass_bands.py (119 lines)

Total: 2,464 lines across 7 modules.

Also traced (per the EXTRA FOCUS instruction) into foreman.py, magnitude.py, standards.py,
pipeline.py and live state under `data/` and `state/` to answer the "the automation reproduces
the charter" red-standard question. Those files are NOT claimed as fully read/audited — only the
specific mechanism was traced with evidence, as instructed.

---

## KNOWN-OPEN ITEMS — CONFIRMED AT SOURCE, UNCHANGED

### 1. assay.py:219–223 — `axis_score()` returns a flat 9.9 for every M10 input
```python
i = LADDER.index(band)
if i + 1 >= len(LADDER):
    return 9.9
```
`LADDER` has 11 entries (M0..M10), indices 0–10. For `band="M10"`, `i=10`, `i+1=11 >= 11` is
always `True`, so the function returns the constant `9.9` regardless of `x`, never touching
`BAND_EDGES["M10"]`. CONFIRMED unchanged, still open.

### 2. assay.py:302–322 — `SIGMA_BY_ATTESTATION` rescale silently discards the calibrated raw sigma
```python
_RAW_SIGMA = {"Instrumented": 2.70, "Witnessed": 4.08, ...}
_SCALE = SIGMA_MAX / max(_RAW_SIGMA.values())        # = 2.8577 / 8.50 = 0.3362
SIGMA_BY_ATTESTATION = {k: round(v * _SCALE, 4) for k, v in _RAW_SIGMA.items()}
```
The adjacent comment (lines 274–284) says 4.08 was solved for specifically to reproduce the
charter's published Kenshiro ±0.12. The table actually shipped is `4.08 * 0.3362 ≈ 1.372`, not
4.08 — the calibrated value is discarded in favor of a ceiling-rescaled one. CONFIRMED unchanged,
still open.

### 3. anchors.py — floor→ceiling invariant genuinely violated; script now correctly reports it
Ran `python anchors.py` live (miniconda, PYTHONIOENCODING=utf-8):
```
monotone floor -> ceiling : False
     The Skate Guy                  0.22
     A Sword                        0.10
     Yggdrasil                      6.18
     Goku                           5.42
     The Seat of the Creator       10.99
EXIT=1
```
Matches the known-open description exactly: A Sword (0.10) sits below The Skate Guy (0.22), and
Goku (5.42) sits below Yggdrasil (6.18). The script's own exit-code fix (lines 236–250,
documented as landing before run #26) is confirmed working — this is a real, live, propagating
instrument-ordering question for the owner, not a script bug. CONFIRMED unchanged.

### 4. derivation.py:476–477 — `SCAN_MODULES` omits physics.py, cosmology_graph.py, magnitude.py, address.py, pantheon.py
```python
SCAN_MODULES = ["assay", "feats", "cosmography", "propagation", "descending_ladder",
                "scale_theories", "chord_field", "resonance", "tempus", "ledger", "rigor",
                "custodes", "weave", "onomast", "worldseed", "address_space", "genre",
                "profile", "tiers", "grounding", "sevenfold", "burgs"]
```
Verified against `ls src/*.py`: `physics.py`, `cosmology_graph.py`, `magnitude.py`, `address.py`,
`pantheon.py` all exist in `src/` and are exactly the kind of module that carries physical/band/
address-width constants the ledger exists to police, yet none of the five names appear in the
list. CONFIRMED unchanged, still open.

---

## EXTRA FOCUS — "the automation reproduces the charter" is RED: mechanism traced

Live files read directly (not simulated):
- `data/CHARTER_REGRESSION.json`: `at=1787541881` → **33.07h old** at time of audit. 5 of 6
  `BENCHMARKS` rows are `status: DEFERRED` ("no transport answered ... retried next run" /
  "no transport carried even the split calls") or `status: NO_SCORE` (Jotaro — "no axis cleared
  its gate"); only Jace Beleren is `SCORED` and `consistent: true`. This reproduces the reported
  `1/1 consistent, 5 unscored, 33h old` line from `standards.py:709-710` exactly.

**Why 5 are unscored (CONFIRMED):** `state/calibrate.log` shows the live model-transport pool is
almost entirely down. Every attempt today logs a stream of `REMOVED <provider>: HTTP 402 (needs
billing on that provider)` for 5 cloud buckets (cb-glm47, ms-codestral, ch-deepseek, di-qwen,
hf-qwen) and `REMOVED local-<model>: HTTP 404 (no such model)` for 5 configured local Ollama
model names that are not actually pulled on this machine (`llama3.1:latest`, `gemma3:12b`,
`qwen2.5:14b`, `qwen3:30b-a3b-instruct-2507-q4_K_M`, and an unsloth GGUF variant). Only
`qwen3:8b` survives as working transport, so `assay_entity()` in magnitude.py falls through to
`DEFERRED`/`NO_SCORE` for entities whose evidence needs split calls the thin pool can't carry
(magnitude.py:611-648).

**What writes the file, and is the producer still running (CONFIRMED, not guessed):**
`magnitude.py`'s `calibrate()` builds all 6 `rows` in one in-memory loop and only writes
`data/CHARTER_REGRESSION.json` (atomically, via `.tmp` + `silence.replace_retry`) **after the
loop finishes** (magnitude.py:808-817). `foreman.py:run_charter_regression()` (line 644) is the
dispatcher: gated on `POOL_PROOF.json` showing ≥3 answering buckets, it launches
`src/magnitude.py --calibrate` as a background job when the "automation reproduces the charter"
standard reads red. `state/foreman.log` for today shows it has NOT stopped — it re-dispatched at
01:38, 02:32, 03:49, 05:27 and 06:30 — but every single one of those runs was killed mid-flight
by the foreman's own "every running job is advancing" → `kill_stalled_job` remedy before it could
reach the final write:
```
[06:30:28] charter regression: starting (background)
[06:xx]    charter regression: charter regression already running
[06:xx]    every running job is advancing -> kill_stalled_job: killed stalled calibrate:52800, ...
```
`magnitude.py --calibrate` is explicitly noted as "NOT in the keeper's STANDING set" — nothing
restarts it promptly; it waits for the supervisor's next MAIN LAP (42-44 min typical, up to 4h
worst case) before `run_charter_regression` even gets to try again, and each retry is grinding
through the same near-empty transport pool slowly enough to get killed as stalled again before
finishing 6 benchmark entities.

**Verdict:** the producer has not stopped — it is actively retrying on a roughly hourly cadence —
but it has not completed a single full pass since the file's current content (33h old) was
written, because (a) the transport pool feeding it is down to one thin local model, which makes
each pass slow, and (b) the foreman's own stall-killer keeps terminating it before it reaches the
write step, in a loop that self-perpetuates. This is a live, ongoing failure loop, not an
abandoned process and not a code bug in any one of my 7 assigned modules — it is a
config/infrastructure state (dead API credits, un-pulled local models) interacting with a
timeout/restart policy in foreman.py.

---

## NEW FINDINGS

### coverage.py:10-18 vs :82-115 — docstring promises 5 states, code only ever returns 4 [HIGH][CONFIRMED]
The module's own docstring lists five mutually exclusive states an entry can sit in, explicitly
including:
```
UNREACHABLE  a host exists but the fetch failed -- the only state that is purely a defect
```
and immediately below that: "The distinction between READ and NO PAGE is the whole point of the
file. Collapsing them is what made every silent failure in this project look like an honest
absence."

But `state_of()` (lines 82-115) has exactly four return points, and all of them return one of
`"NO HOST"`, `"CITED"`, `"READ"`, or the default `best = ("NO PAGE", 0, 0)`. There is no branch
that ever produces `"UNREACHABLE"` — grepped the whole file, the string appears exactly once, in
the docstring. When neither `READ_CACHE` nor `F.CACHE` has a file for an entity (`os.path.getmtime`
raises `OSError`, caught and `continue`d), the function falls straight through to `return best`,
i.e. `"NO PAGE"` — with zero way to tell "the wiki genuinely has no article under this name" apart
from "a fetch was attempted and failed, so no cache file was ever written." That second case is
exactly the failure mode `feats.py:59-60` itself names ("the API is unreachable... another failure
wearing the costume of an absence") — coverage.py's own docstring promises to distinguish it and
the code does not. Failure scenario: a host is real and reachable in general but throttled/
rate-limited/erroring for a specific page fetch (e.g. Wikipedia 429, or a timeout); no cache file
lands for that entry; `state_of()` reports `NO PAGE`, `report()` counts it under "no article under
this name," and the coverage dashboard reads it as an honest absence rather than the "purely a
defect" state the docstring says should exist for exactly this case.

### onomast.py:238-265 — `coin_well_formed`'s last-resort fallback can still return a malformed or duplicate name [MEDIUM][CONFIRMED]
```python
for salt in range(max_tries, max_tries * 25):
    nm = coin_name(f"{base}|{salt}", register)
    if well_formed(nm) and nm.lower() not in taken:
        return nm
silence.note("onomast.py:coin-exhausted")
return coin_name(f"{base}|fallback", register)
```
After 10,000+ deterministic candidates are exhausted, the final line returns a name with **no**
`well_formed()` check and **no** `taken` check — the exact invariant break the surrounding comment
says was "the single code path capable of breaking it silently" (and says was fixed 2026-08-24).
It is now logged (`silence.note`), but the return value itself can still be malformed or a literal
duplicate of an already-issued catalogue name; "Shelfmarks are unique" (one of the 39 standards
per the comment) can still be violated by this path, just with a log entry alongside it now
instead of complete silence. Whether that's an acceptable last-resort tradeoff ("refusing to name
anything would be the worse failure," per the comment) is a legitimate design call — flagging as a
question rather than an outright bug, but noting the invariant genuinely is not fully restored.

Secondary, smaller issue on the same line: `silence.note()` is documented (silence.py:290-296) as
"Record the exception currently being handled" — it reads `sys.exc_info()`. This call site is not
inside an `except:` block (namespace exhaustion is a normal loop-exhaustion path, not a raised
exception), so `sys.exc_info()` returns `(None, None, None)` and the resulting `health.record`
entry carries exception type `"None"` and no sample — a nearly content-free log line
(`silent:onomast.py:coin-exhausted None`) rather than a diagnostic one (no seed, no register, no
`taken` size). Low severity on its own, but it means the "LOUD" failure the comment promises is
in practice a generic, low-information ledger entry.

### onomast.py / address.py — missing the `_BAD_CHARS` corruption guard despite being regex-heavy [MEDIUM][CONFIRMED]
assay.py (lines 42-51) and coverage.py (lines 36-38) both carry a self-check that `raise
SystemExit`s if the module's own source contains a literal backspace/VT/FF/BEL control character —
guarding against the documented, five-times-repeated failure mode where a regex word-boundary
escape arrives through a shell heredoc as a corrupted control byte and "reads as a tuning problem
... rather than as corruption." Grepped: **43 of ~110 modules** in `src/` carry this guard
(`grep -rl _BAD_CHARS src/*.py`), so it is a real, widely-adopted convention, not a one-off.
Of my 7 assigned modules, only assay.py and coverage.py have it. `onomast.py` and `address.py` —
both of which build regex patterns with exactly the escape classes historically hit
(`re.sub(r"\s*\([^)]*\)\s*", ...)` in onomast.py:104; `re.sub(r"[^\w\s-]", ...)`,
`re.split(r"[\s_-]+", ...)` in address.py:120-121) — have **no** such guard. If either module's
source is ever transported through the same heredoc path that bit five earlier modules, the
corruption would again present as "the gate is too strict" / "zero matches" rather than as
corruption, in exactly the two files whose entire job is regex-driven name/address matching.
`derivation.py`, `anchors.py` and `repass_bands.py` do not use raw regex literals with
backslash escapes, so their absence of the guard is lower-risk by comparison.

### derivation.py:534 / onomast.py:389,392 / coverage.py:141,161,166,171 / repass_bands.py:102,108 — console-report truncation under Hard Rule 0 [LOW][CONFIRMED, display-only]
Hard Rule 0 in CLAUDE.md is written to forbid "any cap, sample, truncation, or limit on
anything." Several `main()`/`report()` functions in this batch print only a bounded slice of a
full result set to the console:
- `derivation.py:534` — `for n in sorted(LEDGER, key=lambda x: -depth(x))[:6]:` (top 6 deepest
  chains only, silently, no "N more" note)
- `onomast.py:389,392` — `for endo in sorted(...)[:4]:` and `for v in rows[:9]:` (does print
  `"... and {len(rows)-9} more"` when truncated — the honest version of this pattern)
- `coverage.py:161,166,171` and `--show` default of 26 — `[:12]`, `[:show]`, `[:10]` on the
  worst/best-covered source listings, with no "N more" disclosure
- `repass_bands.py:102,108` — `kept_entries[:14]`, `demoted_entries[:8]` (labelled "a sample of
  what was carrying a Magnitude," which is at least honest about being a sample)

In every one of these cases, the **actual persisted/mutated data is not truncated** — the full
`rows`/`LEDGER`/`named`/records are written or modified in full (`silence.write_json(OUT, rows,
...)` in coverage.py, `silence.write_json(OUT, named, ...)` in onomast.py, `PL.write_record`
called for every changed record in repass_bands.py regardless of what got printed). This is
console-report truncation for human readability, not a truncation of a roster/listing/dataset the
project's own hard-rule examples describe (`roster(limit=600)`, `cap_chunks=12`, etc.). Flagging
because Hard Rule 0's text is unqualified ("no cap... on anything") and this pattern recurs across
4 of my 7 modules — worth an owner call on whether report-only truncation is meant to be exempt
(and if so, whether it should always self-disclose an "N more" count the way onomast.py already
does and coverage.py/derivation.py do not).

### repass_bands.py:98 — hardcoded "of 211" source count [LOW][CONFIRMED]
```python
print(f"  demoted to unassayed: {len(demoted_sources):,} of 211")
```
211 is a magic number, not derived from `recs`/`PL.records()` or any live count in this run.
CLAUDE.md's own text says the roll is "~215 sources" and elsewhere in this project's log output
(magnitude.py comment) the number 211 appears independently, so it may just be stale by a few —
but as written it can never track the real roll size and will silently drift wrong as sources are
added or the unassigned-sources question is resolved. Cosmetic (does not affect the demotion
logic itself, only this one printed denominator), but worth a one-line fix
(`len(set(src for _, rec in recs for src in [rec["source"]]))` or similar) rather than a constant.

### repass_bands.py — long-running batch read-then-write against pipeline.write_record's partial merge protection [MEDIUM][SUSPECTED]
`repass_bands.py` calls `PL.records()` once at the top (`recs = PL.records()`, line 36), holding
every record's JSON in memory as it iterates and only calling `PL.write_record(path, rec)`
per-record later in the same pass (line 84). I read `pipeline.write_record` (pipeline.py:503-540,
outside my assigned batch, but load-bearing here) to check its guarantees: it only re-merges from
the disk copy when the **entry count** has drifted (`len(disk.entries) != len(rec.entries)`,
line 522) — in that case it merges a fixed allowlist of per-entry fields
(`category, scale_note, scale_note_rejected, magnitude, topic, catalogued`) from the in-memory
copy onto the disk copy by name. If the entry **count is unchanged** but a concurrent writer (per
`state/foreman.log`, `pipeline_auto` is in the foreman's STANDING set and is restarted within
300s if it dies — i.e., a live, frequently-running concurrent writer of the same per-entry
fields) modified one of those same fields on the same record between repass_bands.py's initial
read and its later write, `write_record` takes the fast path (`merged = rec`) and overwrites disk
with the stale in-memory copy, silently reverting the concurrent edit. This is a genuine gap in
`write_record`'s protection (it only catches whole-entry drift, not same-count field-level
drift), and `repass_bands.py` is exactly the usage pattern most likely to expose it: it reads
everything up front and may not write a given record back until well after another process has
touched it. Marked SUSPECTED rather than CONFIRMED because I did not reproduce the race live
(would require running repass_bands.py concurrently with pipeline_auto against a shared record and
observing a lost field) and because the fix, if wanted, belongs in pipeline.py's write_record
(outside my assigned modules) rather than in repass_bands.py itself.

### assay.py:226 — `axis_score()`'s `not lo`/`not hi` check is falsy-zero-unsafe (latent, not currently triggered) [LOW][SUSPECTED]
```python
if not lo or not hi or hi <= lo:
    return None
```
Uses truthiness rather than an explicit `is None` check. Every value currently in `BAND_EDGES` is
a positive float, so this is not live-triggered today — but if a future band edge is legitimately
`0` (e.g. a `reach=0` floor at some rung), `axis_score()` would incorrectly return `None` for that
axis/band instead of computing the log-scaled score, because `not 0.0` is `True` in Python. Would
read as "no scale for this axis" rather than as a valid zero-floor band. Low severity, latent.

---

## Checked and found NOT to be problems (worth recording so they aren't re-litigated)

- assay.py:325-374 `_interval()` now correctly receives the caller's `weights=W` override
  (assay.py:426-427) — the "Found 2026-08-24" bug documented in the comment (module-global
  WEIGHTS read against a caller-supplied `denom`) is fixed in the code as shipped; comment and
  code agree.
- assay.py `assay()`'s ceiling-clamp (`_dec >= 1.0` → 0.99, `at_ladder_ceiling`/`promotion_due`)
  is internally consistent; `promotion_watch` recomputes from the unclamped `value`, which is
  mathematically identical to the pre-clamp `_dec`, so it is redundant but not wrong.
- address.py's word-boundary / letter-equality spine-code matching (the documented 2026-08-23 DC
  Comics / Sword Coast collision fix) is present and matches its own description; no regression
  found.
- onomast.py's `well_formed()` four mechanical constraints (length, echo, stutter, cluster) plus
  the consonant-density and vowel-run additions are internally consistent and match their
  comments; no off-by-one found in the trigram/pair-repeat window arithmetic.
- repass_bands.py:78-87 write-gate fix (checking `PL.write_record`'s return value before
  appending to `touched`) is present and matches its own "run #25" changelog comment.
- silence.write_json / silence.replace_retry usage in onomast.py:399 and coverage.py:185 is
  correct per the two-writer contract (atomic temp-file + PID/thread-qualified name + retry).

---

## Modules read and total lines
src/assay.py (649), src/derivation.py (558), src/onomast.py (407), src/address.py (290),
src/anchors.py (250), src/coverage.py (191), src/repass_bands.py (119) — **2,464 lines, 7
modules, every line read.**
