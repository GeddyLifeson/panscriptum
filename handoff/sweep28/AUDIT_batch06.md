# Sweep #28 — batch06 audit

Modules (every line read, 2,491 total): `src/cascade_bridge.py` (1103), `src/health.py` (428),
`src/estate.py` (338), `src/tuning.py` (263), `src/style_audit.py` (211), `src/scale_theories.py`
(148).

NEXT_STEPS.md §3 grepped for all six module names before starting. Prior recorded findings for
this batch: four, all in `cascade_bridge.py` / `health.py` (listed below as KNOWN). No prior
findings existed for `estate.py`, `tuning.py`, `style_audit.py`, `scale_theories.py`.

---

## SPECIAL FOCUS — the `All N candidates failed: <label>` red rows

**Where the string is produced.** Not in this repo. `C:\Users\imarl\cascade\cascade\engine.py:361`:

```python
yield {
    "type": "error",
    "error": f"All {len(tried)} candidates failed: {', '.join(tried)}",
}
```

`tried` is a list of *labels* only (e.g. `"GPT-OSS 120B (Groq)"`) accumulated as the engine walks
its candidate ladder. No status code, no exception text, no provider wording — confirming
`cascade_bridge.py:333-336`'s own claim that this is "an aggregate wrapper... NO disposition."
`cascade_bridge.py` receives this only via the streamed `{"type":"error"}` event
(`cascade_bridge.py:820-822`) or as a raw exception string (`:824-835`); it never invents the
text itself.

**Why the classifier can't name it, precisely.** `cascade_bridge.py:398-402` documents the
design: for a **single**-candidate aggregate (`All 1 candidates failed: <label>`), the pinned
bucket and the failed attempt are known to be the same model, so `pool_exhausted()` (:406-409,
requires `N>1`) returns `False` and the row is deliberately kept eligible for the "unrecognised"
ledger rather than being folded into the pool-capacity signal. Two unwrap attempts then try to
replace the wrapper text with the provider's real complaint, reading Cascade's own
`state/cascade_scratch.db` `bucket_state` table (`bucket TEXT PRIMARY KEY, ..., last_error TEXT,
updated_at REAL` — confirmed via `sqlite_master`, one row per bucket, **overwritten** on every
attempt, not a history):

  - narrow, 180s (`cascade_bridge.py:925-928`, via `provider_error(bucket)` default
    `max_age_s=180`) — used because a stale row must never justify a 4-hour bench (m103's harm).
  - wide, 6h (`cascade_bridge.py:972-976`, `provider_error(bucket, max_age_s=6*3600)`) — added
    specifically because "the aggregate arrives more than 180s after the provider row that
    explains it" (comment at `:955-965`, citing this exact row:
    `groq:openai/gpt-oss-120b: All 1 candidates failed: GPT-OSS 120B (Groq)`, thirty occurrences).

**What the underlying provider error actually is — verified live, right now, against the
running state on disk:**

```
$ sqlite3-equivalent query against state/cascade_scratch.db (mode=ro), just now:
groq:openai/gpt-oss-120b  (age 0.03h / ~108s)
  {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` ... tokens per day
  (TPD): Limit 200000, Used 199999, Requested 2815. Please try again in 20m15.648s. ..."}}
sambanova:free  (age 0.2h / ~720s)
  {"error":{"message":"Rate limit exceeded","type":"rate_limit_exceeded", ...}}
zai:free  (age 0.2h / ~720s)
  {"error":{"code":"1113","message":"Insufficient balance or no resource package. Please
  recharge."}}
```

So: Groq is genuinely pinned against its 200,000-token daily cap (confirms NEXT_STEPS §4's
"Groq tokens-per-day rate limit" conclusion, re-verified live); SambaNova is an ordinary
per-minute rate limit; Z.AI is the exact "insufficient balance" condition
`cascade_bridge.py:461-465,872-876` says was the whole reason this classifier was built (and
which is a listed `permanent_words` phrase at `:930` — it should be earning `zai:free` a 4-hour
`AUTH_BENCH`, not sitting unrecognised).

**NEW finding (HIGH), the actual live gap.** `state/POOL_UNRECOGNISED.json`, read the same
moment, holds — for the *exact same three buckets* — rows that are **5.6–5.9 hours stale** and
still carry the bare wrapper text:

```
groq:openai/gpt-oss-120b|All 1 candidates failed: GPT-OSS 120B (Groq)   count=30 last_seen=5.67h ago
sambanova:free|All 1 candidates failed: DeepSeek V3 (SambaNova)         count=4  last_seen=5.67h ago
zai:free|All 1 candidates failed: GLM 4.7 Flash (Z.AI)                  count=4  last_seen=5.67h ago
```

(There is also, separately, exactly **one** row per bucket where the wide-unwrap *did* land —
e.g. `groq:openai/gpt-oss-120b|{"error":{"message":"rate limit reached...` at count=1 — proving
the unwrap mechanism works *sometimes*, which makes the 30-vs-1 split the interesting fact, not
"the unwrap never works.")

The reason these 30/4/4 stale rows never get corrected: **`unrecognised_open()`
(`cascade_bridge.py:545-584`), the function `standards.py` reads to render the `every pool
failure is recognised` row, never re-attempts `provider_error()`.** Its own docstring says it
is "RE-TRIAGED ON READ" — but that re-triage is only against the three *classifier predicates*
(`pool_exhausted`, `named_transient`, `empty_content`) run over the **frozen `error` string
captured at write time** (`:577-579`). It never re-runs the unwrap against a *fresher*
`bucket_state` snapshot. So: the moment `record_unrecognised()` is called and both the 180s and
6h lookups happen to lose the race against `bucket_state`'s single-row-per-bucket,
overwritten-on-every-attempt design (plausible mechanism, not fully provable without Cascade's
router-side write ordering: many workers can hit the *same* bucket concurrently, and the one
row reflects whichever attempt wrote last, not necessarily the attempt that is being classified)
— the wrapper text is locked in for that row's entire life, even though, as proven above, the
real explanation reliably becomes available again in the very same table within minutes. A
human reading the live `standards` page right now sees "unrecognised" for a fault whose plain-
English cause (Groq TPD, SambaNova throttle, Z.AI billing) is sitting, timestamped seconds ago,
in `state/cascade_scratch.db`.

**Fix shape (not applied — auditor does not edit):** either have `unrecognised_open()` attempt a
fresh, wide `provider_error()` lookup per row before returning it (cheap: one more SQL read per
row, already read-only), or have `record_unrecognised()` retry the wide unwrap once more on a
short delay before giving up. Either closes the "one window, one shot" gap the code's own
comments (`:955-965`) already diagnosed but did not fully close.

---

## src/cascade_bridge.py (1103 lines, fully read)

### KNOWN — still open, re-verified
- **`:225-234` `_interval()`** returns `0.0` (no pacing) on *any* exception from
  `_ROUTER.limits_for(bucket)`. Confirmed unchanged. A silent transport error here reads
  identically to "this bucket declares no rate limit," collapsing failure into a success-shaped
  default before the pacing gate that exists specifically to stop 429 storms.
- **`:502-542` `record_unrecognised()`** — the in-file comment (`:530-536`) is accurate: the
  *write* race is fixed (`silence.write_json` gives each writer a pid+thread-unique tmp name).
  The *read-modify-write* of the `rows` dict itself (read `:518-521`, mutate in memory, write
  `:537`) is protected only by `_UNREC_LOCK`, a `threading.Lock` (`:331`) — process-local. Two
  processes (this file is imported by `read`, `pipeline`, `feats`, `overwatch` per the same
  comment) can each read the same `rows`, each add their own increment, and the last writer's
  `silence.write_json()` call silently discards the other's count. File integrity is preserved;
  the counter can still lose updates cross-process. STILL OPEN, exactly as filed.

### NEW
See "SPECIAL FOCUS" above — the `unrecognised_open()` no-re-unwrap-on-read gap
(`:545-584`, HIGH).

---

## src/health.py (428 lines, fully read)

### KNOWN — still open, re-verified and refined
- **`:220-253` `check_caches()`** — `files[:200]` (`:241`) and `n = min(len(files), 200)`
  (`:250`) sample at most 200 files per host directory with no disclosure that a host with more
  than 200 cache files is only partially checked. Confirmed unchanged. Hard Rule 0 shape.
- **`:61-144` `flush()`'s RMW on `state/failures.json`.** NEXT_STEPS describes this as "has a
  threading.Lock only." Verified more precisely: `grep -n "_LOCK" src/health.py` shows `_LOCK`
  used in exactly one place, `record()` (`:76`) — **`flush()` (`:85-144`) never acquires `_LOCK`
  at all**, around either the read-merge of `prev` (`:89-103`) or the iteration/clear of the
  shared `LEDGER` Counter (`:102`, `:123`). So the RMW is unprotected even *within one process*,
  not merely under-protected across processes. The concrete, provable consequence is the same
  lost-update race NEXT_STEPS names (two `flush()` calls read the same on-disk `prev`, each
  merges its own `LEDGER`, the later `silence.replace_retry()` clobbers the earlier merge's
  counts). I additionally tried to reproduce a `RuntimeError: dictionary changed size during
  iteration` crash (a concurrent `record()` inserting a new key while `flush()` iterates
  `LEDGER.items()`) with a targeted ~20,000-operation stress script; it did **not** trigger in
  that test, so I am flagging the crash risk as theoretically possible but **unproven**, while
  the "no lock is held" fact itself is directly confirmed by grep.

### NEW
- **`:119` (`flush()`) and `:361` (`reopen_stranded()`) — fixed-name `.tmp`, not
  `silence.write_json`.** Both hand-roll `tmp = path + ".tmp"` then `open(tmp, "w")` +
  `json.dump` + `silence.replace_retry(tmp, path)`. `silence.write_json` (`silence.py:250-287`)
  exists specifically to close this: its own docstring says a fixed `path + ".tmp"` lets two
  writers of the *same path* "collide on the temp file itself," and "the loser can replace the
  winner's target with a partial file" — worse than a lost update, a genuinely wrong file landing
  at the destination. `cascade_bridge.py:530-536` independently makes the identical point about
  the identical pattern. `health.py:105` calls `state/failures.json` "the highest-traffic shared
  file in the project" and `health.py:359` calls `state/PIPELINE_STATE.json` "the single most
  important state file in the kit" — both are written this way, by a module imported into every
  one-shot subprocess in the tree. `silence.replace_retry()` protects the final rename from
  landing a *torn* file, but does nothing about two processes' `open(tmp, "w")` calls racing on
  the identical filename before that rename runs. Severity HIGH given the files named.
- **`:352` `reopen_stranded()` console print** — `for k in reopen[:20]:` truncates only the
  printed list of which batch keys would be/were reopened; the actual repair at `:355` correctly
  operates on the full, uncapped `reopen` list. No data lost, but it is the Hard-Rule-0
  "truncated diagnostic" shape (lesson 16) applied to a repair tool's own confirmation output.
  LOW.

### Read, no issues found
`record()` (:71-82), `summary()` (:147-151), `check_control_chars()` (:156-165),
`check_context_budget()` (:168-188), `check_api_paths()` (:191-217), `check_state()` (:256-307,
the M20 positional-done-marker issue is already an OWNER RULING item in NEXT_STEPS §1/§4 and is
narrated accurately in this file's own comments — not re-filed here), `preflight()`/`main()`
(:374-429).

---

## src/estate.py (338 lines, fully read)

### KNOWN
None on file for this module (confirmed via grep of NEXT_STEPS.md).

### NEW
- **`:209-211` charter erratum check is unconditionally true, MED.**
  ```python
  for rung in ("Supercluster", "Filament", "Hyperverse"):
      if rung.lower() in text.lower():
          note("charter erratum (open)", rung + " is a rung with no Magnitude band")
  ```
  This only tests whether the rung's *name* appears anywhere in the charter text — not whether
  it actually still lacks a Magnitude band, which is the claimed defect. Since these are real,
  named rungs the charter necessarily discusses at length, the condition is true by construction
  and can never turn false: fixing the underlying charter defect (adding Magnitude bands for
  these three rungs) would not change this check's output at all, because the check never looks
  at bands — only at the rung's name existing. This is "a check that cannot fail" in the
  "always positive" direction: it can never observe a fix, and it would equally fire on an
  unrelated future edit that merely happens to mention "Filament." Docstring at `:158-161`
  presents this as a maintained, checkable erratum; the code cannot actually check it.
- **`:197` `un[:4]`, LOW.** `note("catalogued sources with NO charter spine code", f"{len(un)} —
  e.g. " + ", ".join(un[:4]))` — the reported *count* (`len(un)`) stays honest, but the example
  list is capped to 4. Same shape as the Hard-Rule-0 "truncated diagnostic" pattern flagged
  repeatedly elsewhere in NEXT_STEPS (lesson 16): if the sources that most need attention are
  outside the first four (alphabetical-ish, from `sorted(recs - set(codes))`), they are invisible
  here.

### Read, no issues found
`_walk`/`inspect`/`artifacts` (:53-147) — genuinely exhaustive, no sampling, matches the module's
own stated purpose. `written()` (:217-257), `terminal()` (:262-289), `external()` (:294-338).

---

## src/tuning.py (263 lines, fully read)

### KNOWN
None on file for this module. (Directly relevant to OWNER RULING M19 in NEXT_STEPS §1, which
this module implements the `regime()`/`profile()`/`workers()` machinery for — that ruling is
about *policy*, not a code bug, and is not re-filed here.)

### NEW
- **`:203` contradicts its own docstring, MED.**
  ```python
  if n >= CLOUD_MIN_BUCKETS and (not judged or rate >= CLOUD_MIN_SUCCESS):
      r = "cloud"
  ```
  The comment immediately above (`:68-82`) states plainly: "the label now requires both: enough
  buckets answering AND a measured success rate at or above this floor" — framed as *the* fix
  for "the project's most-repeated defect" (certifying reachability as capacity, named at four
  other sites: m59, M8, m66, foreman's catalogue gate). But the boolean only enforces the rate
  requirement when `judged` is `True` (`rate is not None and calls >= MIN_CALLS_TO_JUDGE=20`,
  `:200`). At the start of every run, or any time fewer than 20 cloud calls have landed in the
  measurement window, `judged` is `False` and `(not judged or ...)` is `True` unconditionally —
  so `regime()` falls back to exactly the reachability-only test the surrounding comment says was
  retired. This is the precise code-level mechanism behind NEXT_STEPS §1 M19's observation that
  "the loop is self-feeding — narrow gate → few calls → noisy sample → narrow gate": the
  fallback to reachability-only during exactly the low-data periods is not a coincidence of the
  loop, it is written into `regime()`'s own condition.

### Read, no issues found
`_ollama_host()`/`_ollama_up()` (:107-136, the m59/M8/m66-class host-mismatch bug this file's own
comment describes is closed here, correctly reads `config.yaml`), `_answering_buckets()`
(:138-157), `cloud_success_rate()` (:160-186), `profile()` (:215-223), `workers()` (:226-244,
the "0 is a request, not an absence" fix at `:233-241` is correctly implemented —
`min(requested, n) if requested is not None else n` yields `0` for `requested=0`), `main()`
(:247-263).

---

## src/style_audit.py (211 lines, fully read)

### KNOWN
None on file for this module.

### NEW
- **`:38-39` `TURN_ENDING` regex over-matches mid-record turns, MED, reproduced.**
  ```python
  TURN_ENDING = re.compile(
      r"(?:\.|\?)\s+(?:And|But|Yet|Still|Which|That)\b[^.]{0,80}\.\s*$", re.M)
  ```
  `re.M` makes `$` match end-of-*line*, not end of the record string. `record_of()` extracts
  record text with `re.S` (dot-matches-newline), so a record legitimately containing an embedded
  `\n` (a paragraph break inside "The Record" prose) can have a turn-shaped sentence *mid-record*
  register as a match, because that sentence happens to end at a line break, long before the
  record's actual final sentence. Reproduced directly:
  ```python
  r = ("It was built in the third age. But it did not last.\n"
       "She rebuilt the tower stone by stone, testing every joint against frost and time, "
       "until the work itself became a form of memory.")
  bool(TURN_ENDING.search(r))   # -> True
  ```
  The record's real ending is not a turn at all, but `TURN_ENDING.search()` still matches,
  because of the embedded newline. This inflates `turn_rate` (`audit()` :113-114, :129), which
  `report()` (:168-169) flags red once it exceeds 25% — a false positive that can make honest
  prose look over-turned, or (the more dangerous direction for a style QA tool) dilute a
  genuinely-elevated true rate with false positives scattered across otherwise-clean entries,
  masking which entries actually need a rewrite. Fix shape: anchor on the true end of `r`
  (`re.search(..., re.S)` without `re.M`, or explicit `r.rstrip()[-N:]`) rather than any line
  ending inside it.
- **`report()` truncates four separate printed panels, LOW–MED (presentation-only).**
  `a["shapes"].most_common(top=8)` (:143), `a["openers"].most_common(top=8)` (:148),
  `sorted(a["banned"].items(), ...)[:14]` (:157), `a["vocab"].most_common(10)` (:172). The
  underlying `audit()` Counters (:104-133) are themselves complete and uncapped — only the CLI
  report view truncates, and `len(a['banned'])` is printed alongside as the true distinct-tell
  count (:161), so the cap does not corrupt any downstream data. Flagging per the project's
  literal Hard Rule 0 text ("no truncation... of an entry list") and lesson 16's warning that a
  capped *diagnostic* can hide exactly the row that most needs to be seen — here, whichever
  banned construction or vocabulary word ranks 15th instead of 14th, or whichever opener repeats
  9th-most instead of in the top 8, is invisible to a run's operator even though the module's own
  stated purpose (catch cross-chapter repetition at 52,000-entry scale) is precisely the case
  where the long tail matters.
- **`:44` `[◈◈]` duplicate codepoint, LOW, cosmetic.** Both characters in the class are
  literally the same codepoint (`U+25C8` DIAMOND, verified via `ord()`); grepping
  `prompts/system_style.txt` and `prompts/chapter_prompt.txt` confirms only one entry-marker
  glyph (`◈`) is ever used. Harmless (a regex character class de-duplicates), almost certainly a
  copy-paste artifact, no functional effect.

### Read, no issues found
`opener()`/`opener_shape()`/`FUNCTION`/`TEMPLATE_WORDS` (:54-101), `main()`/`--self-test`
(:177-211, the self-test does exercise a genuinely repetitive corpus and would catch a checker
that stopped detecting repetition entirely).

---

## src/scale_theories.py (148 lines, fully read)

Self-contained fictional-physics helper: a static `THEORIES` dict plus four pure functions
(`bulk_export_beta`, `growth_strike`, `penetration_pressure`, `surviving_theory`). No file I/O,
no shared state, no writes, no `except` blocks, no caps. Every divide-by-zero site is guarded
(`max(growth_time_s, 1e-6)` at `:128`, `max(contact_area_m2, 1e-30)` at `:142`,
`resident_mass_kg <= 0` guarded at `:116`). `surviving_theory()` (:145-148) correctly matches
only `T3_BULK_EXPORT`, the sole entry whose `falsified_by` starts with `"Nothing attested"`.

**No findings.** Read in full; clean.

---

## Severity / status tally

| # | Sev | Status | Location | Claim |
|---|-----|--------|----------|-------|
| 1 | HIGH | NEW | `cascade_bridge.py:545-584` | `unrecognised_open()` never re-attempts `provider_error()` on read; live-proven stale rows (30/4/4) sit unexplained for hours after the real cause reappears in `bucket_state` |
| 2 | HIGH | KNOWN | `cascade_bridge.py:225-234` | `_interval()` returns `0.0` (no pacing) on any exception |
| 3 | HIGH | KNOWN | `cascade_bridge.py:502-542` | `record_unrecognised` RMW lost-update race across processes (write-collision half only is fixed) |
| 4 | HIGH | KNOWN (refined) | `health.py:61-144` | `flush()` holds **no lock at all** (grep-confirmed), not merely a process-local one; RMW lost-update on `state/failures.json` reproducible in principle |
| 5 | HIGH | NEW | `health.py:119,361` | `flush()`/`reopen_stranded()` hand-roll fixed-name `path+".tmp"` instead of `silence.write_json`, on the two files this module's own comments call the highest-traffic and single-most-important shared state files |
| 6 | MED | KNOWN | `health.py:220-253` | `check_caches()` samples `files[:200]` per host dir, no disclosure |
| 7 | MED | NEW | `estate.py:209-211` | charter erratum check tests rung-name presence, not the claimed missing-Magnitude-band defect; can never observe a fix |
| 8 | MED | NEW | `tuning.py:203` | `regime()` skips the success-rate requirement whenever `judged=False` (<20 recent calls), contradicting its own "requires both" docstring |
| 9 | MED | NEW, reproduced | `style_audit.py:38-39` | `TURN_ENDING`'s `re.M` `$` matches mid-record line ends, inflating `turn_rate` on any multi-line record |
| 10 | LOW | NEW | `estate.py:197` | `un[:4]` truncates example list (count stays honest) |
| 11 | LOW | NEW | `health.py:352` | `reopen[:20]` truncates only the console confirmation, not the repair itself |
| 12 | LOW | NEW | `style_audit.py:143,148,157,172` | four report panels truncated (`top=8`/`[:14]`/`most_common(10)`); underlying data uncapped |
| 13 | LOW | NEW | `style_audit.py:44` | `[◈◈]` duplicate codepoint, cosmetic, no functional effect |

`scale_theories.py`: no findings, clean.
