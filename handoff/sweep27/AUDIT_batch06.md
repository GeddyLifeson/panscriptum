# Sweep 27 — Batch 06 audit

Modules read in full (no sampling): src/cascade_bridge.py (1103 lines), src/silence.py (425
lines), src/estate.py (338 lines), src/tuning.py (263 lines), src/style_audit.py (211 lines),
src/scale_theories.py (148 lines). Total 2488 lines. Also read (read-only, for tracing context
only, not part of this batch's edit surface): C:\Users\imarl\cascade\cascade\router.py (the
Router class cascade_bridge.py claims against) and C:\Users\imarl\cascade\config.json.

No files were edited. This is a finder report only.

---

## PRIORITY: the claim/rotation trace (cascade_bridge.py)

### P1. The primary claim loop has NO rotation of its own; it inherits the Router's ranking verbatim, and that ranking is nearly static per call — CONFIRMED, HIGH

`cascade_bridge.py:710-728`:

```python
for _ in range(4 if pin is None else 0):
    claimed = _ROUTER.claim(pool, 1)
    if not claimed:
        break
    cand = claimed[0]
    if cand.bucket.startswith(LOCAL_PREFIX):
        _ROUTER.release(cand)
        continue
    if _alive(cand.bucket):
        pinned = cand
        break
    _ROUTER.release(cand)
```

This takes candidate `[0]` of whatever `_ROUTER.claim(pool, 1)` returns and, if it's alive by
cascade_bridge's own bookkeeping, uses it immediately. There is no sort, no offset, no "skip the
bucket I used last time" — all selection logic is delegated to the Router.

Traced into `C:\Users\imarl\cascade\cascade\router.py`:

- `config.json:6` sets `"strategy": "quality_first"` (confirmed by direct read).
- `router.py:340-376` `_order()` sorts candidates by
  `key = (cost_tier, -rank, 0 if model.local else 1, -headroom)` under quality_first. `rank` is
  a fixed per-model config value (see below), only nudged by a reliability penalty
  (`rank -= int(RELIABILITY_WEIGHT * failure_rate)`), so between calls where nothing has failed,
  the ordering is IDENTICAL every time.
- `router.py:456-485` `_claim_locked()` re-sorts that ranking by `(inflight, order)` — i.e. it
  DOES spread load across buckets, but only in proportion to how many claims are concurrently
  in flight right now. `cascade_bridge._ask_call` releases its claim in the `finally` block
  (`cascade_bridge.py:982-984`) as soon as one call finishes, so with low concurrency, inflight
  is back to 0 by the time the next `ask()` call claims — meaning the router's own
  headroom-based fan-out mechanism never activates, and `claim()` just returns the same
  top-ranked-and-currently-available bucket over and over.

Checked `config.json` directly: the "coding" pool (the pool every caller of `cascade_bridge.ask`
uses by default — grepped `src/*.py`, no caller passes an explicit `pool=`) has 40 of 42 models
tagged into it, across 27 distinct buckets (verified by script, not the "sixteen buckets" this
file's own comment claims — see P4). Ranked by config `rank` (excluding the 3 disabled/paid
Anthropic entries, since `allow_paid=false`), the top non-paid, non-local bucket is
`nv-qwen3-coder` / bucket `nvidia:free` (rank 89), immediately followed by the five `gemini:*`
entries (rank 88 down to 70). This matches the run's own observation that "nvidia:free plus
gemini serve nearly every call" exactly: those are the highest-config-rank ALIVE buckets in a
40-model pool, so the primary loop's very first `claim()` call succeeds against one of them on
attempt #1 almost every time. The other 25 cloud buckets never get tried because the primary
loop never needs to retry past attempt #1, and the WIDEN fallback (see P2) — the only branch in
this file that contains any round-robin logic at all — is reached only when `pinned is None`
after the whole primary loop fails, which essentially requires the top few buckets to be
simultaneously exhausted or benched.

**Concrete failure scenario:** two sequential `ask()` calls, 30+ seconds apart (matching the
observed ~112 calls/hour ≈ 1 every 32s), with `nvidia:free` under its rpm/rpd cap both times.
Call 1: `claim()` ranks `nv-qwen3-coder` first (inflight=0 everywhere), reserves it, returns it;
`_ask_call` uses it, releases it in `finally`. Call 2: `claim()` re-ranks from scratch — inflight
is 0 again for every bucket — and returns `nv-qwen3-coder` again, for the identical reason. This
repeats until `nvidia:free`'s own window is exhausted, at which point the next-highest-rank
alive bucket (a `gemini:*` entry) takes over the same way. 27 buckets with real headroom (per
the run's own count) never enter rotation because nothing in this file or the router ever asks
"has this bucket served relatively more of the recent traffic than its peers" outside the
narrow, rarely-reached widen path.

**Whether this is a bug or a deliberate `quality_first` design choice is a real question** — the
strategy name and the paid-lane-preference logic (`cost_tier` sorts first) suggest the router's
intended posture generally IS "best model available, not spread-the-love." But this file's own
module docstring (`cascade_bridge.py:9-13`) frames the workload as explicitly
"embarrassingly parallel" work meant to exploit eleven providers' worth of small quotas — which
argues for a `spread`-style strategy (also defined in `router.py:370-371`, unused here) or for
this file adding its own breadth-seeking layer on top of `quality_first`, the way the widen path
already does for the narrower case. As written, only the widen path spreads load; the primary
path — which serves nearly every call — does not.

### P2. The widen-fallback round robin is real and correct, but effectively unreachable under current traffic — CONFIRMED (code correctness), SUSPECTED (unreachability at current call volume)

`cascade_bridge.py:729-790`. Traced the rotation logic at 763-779 by hand with a worked example
(5 candidates, 3 "answering" per POOL_PROOF) — the stable double-sort (`sort by answering`,
rotate by `_WIDEN_RR[0] % len(ranked)`, `sort by answering` again) genuinely rotates the
*starting point within* the answering-first group across calls; it is not a no-op. This path is
correctly guarded by `_RR_LOCK` against concurrent cursor races.

The gap is reachability: this branch only runs when `pinned is None and pin is None` after the
primary loop's 4 attempts. Given P1 (the primary loop's first attempt succeeds almost every time
against `nvidia:free`/`gemini:*`), the widen path — the ONLY place in this file with rotation —
is exercised only in the narrow window where those top few buckets are simultaneously
unavailable, which is not the common case implied by the run's own numbers (29 of 30-odd buckets
have headroom; the pool is far from collectively exhausted).

### P3. Bench state cascade_bridge keeps (`_DEAD`) is invisible to the Router's own ranking — SUSPECTED, MEDIUM

`cascade_bridge.py:598-631` (`_alive`, `_bury`) maintain a module-level `_DEAD` dict, entirely
separate from the Router's own `bucket_state`/cooldown tracking in `router.py` (which is backed
by the store and driven by `record_rate_limit`/actual 429s, not by cascade_bridge's own
deadline/auth logic). `_ROUTER.claim()` therefore has no idea a bucket is benched by
cascade_bridge and can hand it back on a subsequent primary-loop attempt; cascade_bridge detects
this via `_alive()` and releases+continues (`cascade_bridge.py:725-728`), but nothing about the
router's ranking has changed between attempts, so if the TOP-ranked bucket is the one
cascade_bridge just privately benched, the loop is likely to re-claim and re-release that same
bucket on subsequent attempts within the same 4-try budget rather than reach a lower-ranked but
genuinely idle bucket — burning retry attempts on a bucket that was already ruled out, before
falling through to widen. Not runtime-verified (would need a live trace with a bucket in
cascade_bridge's private bench), but it follows directly from the two independent state stores
existing side by side with no cross-notification.

**How long a bench lasts (asked explicitly):** `cascade_bridge.py:615-631` `_bury()`. A graded
bench: first miss = `FIRST_BENCH` = 60s; each further consecutive strike doubles it
(`FIRST_BENCH * 2**(n-1)`), capped at `MAX_BENCH` = 900s (15 min); any success clears strikes via
`_clear()` (line 634-638). An auth/billing-shaped failure (401/402/403 or a matching phrase —
`cascade_bridge.py:929-934`) instead gets a flat `AUTH_BENCH` = 4×3600 = 4 hours
(`cascade_bridge.py:175`). A silent deadline timeout (no reply within `timeout`, default 75s)
triggers the graded bench, not the auth one (`cascade_bridge.py:858-862`).

### P4. Stale bucket-count comments — CONFIRMED, LOW-MEDIUM

`cascade_bridge.py:259-266` (`cloud_buckets()` docstring): "Five of this pool's sixteen buckets
are local Ollama models." Checked against the live `config.json` directly: the "coding" pool now
has 40 tagged models across **27 distinct buckets**, of which local models occupy only **2**
distinct bucket names (`ollama:implicit`, `ollama:local`, covering 6 of 42 total models) — not
"five of sixteen." A maintainer reasoning about how many idle cloud buckets *should* exist from
this docstring would underestimate pool width by roughly 40%, which matters directly for
diagnosing "29 of 30-odd buckets idle."

`cascade_bridge.py:734-739`: "`cloud_buckets("coding")` therefore reports FOUR buckets --
cerebras, chutes, deepinfra, huggingface." This one reads as narration of a specific past
incident (unlike its neighbours it carries no date stamp in this exact spot, unlike most of this
file's other incident comments), so it may be intentional historical evidence rather than a
live claim — flagged as a question rather than asserted as wrong — but it is also now
numerically stale against the current 27-bucket pool and could mislead a reader who takes it as
current.

### P5. `record_unrecognised` — a genuine cross-process lost-update race, and the comment beside it appears to declare it solved when it only half-solves it — CONFIRMED, MEDIUM-HIGH

`cascade_bridge.py:502-542`. The function does: read `UNRECOGNISED` JSON (517-521), mutate
`rows[key]` in memory (524-529), then `silence.write_json(UNRECOGNISED, rows, ...)` (537) — a
classic read-modify-write — guarded only by `_UNREC_LOCK = threading.Lock()`
(`cascade_bridge.py:331`). A `threading.Lock` orders threads WITHIN one process; it provides
zero exclusion across processes. The function's own comment at 530-536 explicitly states "this
file is written from every process that imports `cascade_bridge` (read, pipeline, feats,
overwatch)" and then argues the hazard is closed because `silence.write_json`'s pid+thread-unique
temp name makes colliding "on the temp file itself... unavailable to get wrong." That is true
for the WRITE step (two processes' temp files can't collide with each other), but it says nothing
about the READ-then-MUTATE-then-WRITE sequence being atomic across processes — it isn't, and
nothing in this function makes it so.

**Concrete failure scenario:** `read.py` and `pipeline.py`, both live and both importing
`cascade_bridge` (per the module's own comment), each hit the same `groq:openai/gpt-oss-120b:
All 1 candidates failed` error within the same window. Both read the row at `count: 30`. Both
compute `count: 31` in memory. Both call `write_json`. The second `os.replace` wins outright
(last writer wins), landing `count: 31` on disk — the true occurrence count was 32, and the loss
is permanent and silent. Since this ledger exists specifically to make otherwise-invisible pool
failures countable and investigable (`unrecognised_open()` and `standards.py` read `count` to
decide severity/staleness), an undercount here quietly weakens the exact diagnostic this file's
own history (m100, m132, run #26) was built to strengthen — the same class of defect this
project keeps re-finding, recurring in the file whose job is finding it.

### P6. `_interval()` defaults to "no pacing" (0.0s) on ANY exception fetching a bucket's rate limit — CONFIRMED as code; impact SUSPECTED

`cascade_bridge.py:225-234`:

```python
def _interval(bucket):
    try:
        rpm = (_ROUTER.limits_for(bucket) or {}).get("rpm")
    except Exception:
        silence.note("cascade_bridge.py:interval")
        return 0.0
    if not rpm or rpm <= 0:
        return 0.0
    return min(MAX_PACE_SECONDS, 60.0 / float(rpm))
```

`_ROUTER.limits_for()` (traced into `router.py:207-224`) calls `self.store.bucket_state(bucket)`,
which is a live SQLite read against `cascade_scratch.db` — a store this file's own comments
elsewhere describe as being hit by multiple concurrent workers/processes and as a source of
`sqlite3` contention (`cascade_bridge.py:88-91` describes a related SQLite-across-threads
failure mode for the Engine). If that read raises (lock contention, a transient I/O error), the
except swallows it and returns 0.0 — i.e. the SAME "no pacing at all" answer as "this bucket
genuinely has no declared rpm." Given the extended comment block directly above `_pace()`
(`cascade_bridge.py:205-222`) describes this exact mechanism as the fix for "9 workers ...
4% of calls succeeding" against a low-rpm free tier, an error path that silently falls back to
the pre-fix behaviour — and does so preferentially at exactly the moments of highest DB
contention, i.e. highest concurrency, i.e. when pacing matters most — is the dangerous-direction
default this project's lens is looking for. Not independently measured how often
`limits_for()` actually raises in practice.

### P7. `record_unrecognised`'s dedup key truncates to 80 characters before folding — SUSPECTED, LOW

`cascade_bridge.py:514`: `key = bucket + "|" + text[:80].lower()`. Two distinct provider errors
that share an identical first-80-character prefix but diverge afterward (plausible given how
many of these messages are boilerplate-prefixed, e.g. "All 1 candidates failed: ...") would
collapse into one ledger row; the unconditional `r["error"] = text` on line 526 means the
NEWER message's full text silently overwrites the older one's in that row, while `count`
increments as if they were the same fault. Not confirmed against real captured error text from
this run — flagged as a plausible edge case given the file's own history of exactly this kind of
key-folding mistake (m132, run #26, both cited in the surrounding comments).

---

## silence.py (425 lines)

### S1. `_handlers()` known-open bug, confirmed still present — CONFIRMED, HIGH

`silence.py:115-138`. `uses_exc = bool(node.name) and node.name in body` is true for essentially
any `except X as name:`, because `body = ast.dump(node)` includes the handler's own `name=`
field as literal text (e.g. `name='exc'`), so testing whether the string `exc` appears inside
the dump of a node that itself contains `name='exc'` is trivially true regardless of whether
`exc` is ever referenced inside the handler's body. Separately, `records` substring-matches
`"log"`/`"record"` against the ENTIRE dump text (identifiers included), so a handler containing
any unrelated identifier with "log" or "record" as a substring (e.g. a local variable literally
named `records`, or `catalog`) is misclassified as "observed" even though nothing about the
failure was actually recorded.

**Failure scenario:** `except Exception as e: return None` anywhere in the tree — the exact
silent-swallow shape this whole file exists to catch — is scored `silent=False` by `_handlers()`
because `node.name` ("e") trivially matches inside `ast.dump(node)`'s own `name='e'` field. The
audit under-counts true silence.

### S2. NEW: `_handlers()` itself silently drops any file it can't read or parse, with zero diagnostic — CONFIRMED, MEDIUM-HIGH

`silence.py:115-122`:

```python
def _handlers(path):
    try:
        with open(path, encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src)
    except Exception:
        return []
```

No `silence.note`, no print, no record of any kind — a file that fails to open (encoding error)
or fails to parse (syntax error) is treated identically to a file with genuinely zero exception
handlers: it silently contributes 0 to both `observed` and `silent` totals in the audit's
printed report (`main()`, lines 149-182). An operator reading "SILENCE AUDIT — N exception
handlers in src/" has no way to know N excludes any file that couldn't be read at all — the
report can under-state the true handler count with no visible symptom. This is the identical
defect class this file's own docstring (lines 24-25, 42-45) describes as the project's signature
bug, occurring inside the tool built to find it.

### S3. NEW: the identical pattern recurs in `instrument()`, unvisited by whatever fixed anything nearby — CONFIRMED, MEDIUM

`silence.py:378-381`, inside `instrument()`:

```python
try:
    tree = ast.parse(original)
except Exception:
    continue
```

Same silent-skip: a file that fails to parse during `--instrument` is dropped from the "changed"
report with no message at all — `main()`'s printed summary (`instrumented N silent handlers
across M modules`) would simply not mention that file, indistinguishable from "this file had
nothing to instrument." Per the sweep's "ALSO WATCH FOR" guidance (a fix applied to one
construction while the identical one in a sibling function goes unvisited) — S2 and S3 are the
same shape twice in the same file.

### S4. `instrument()`'s file rewrite is a non-atomic `open(path, "w")` on project source — LOW

`silence.py:415-419`. A `.presilence` backup is written first (mitigating real data loss), but
the actual rewrite (`with open(path, "w", encoding="utf-8") as f: f.write(src)`) is a plain
truncate-then-fill, not routed through `silence.write_json`/`replace_retry`. This is a
manually-invoked, single-operator maintenance command over `.py` files, not concurrently-shared
`data/`/`state/` JSON, so the two-writer contract doesn't strictly apply — noting it because it's
the one place in this batch where a raw `open(...,"w")` writes a file that matters without an
atomic replace, and a crash mid-write would leave a truncated source file (recoverable via the
backup, but not automatically).

---

## estate.py (338 lines)

### E1. `charter()`'s errata check can never detect that an erratum was fixed — CONFIRMED, MEDIUM

`estate.py:208-211`:

```python
for rung in ("Supercluster", "Filament", "Hyperverse"):
    if rung.lower() in text.lower():
        note("charter erratum (open)", rung + " is a rung with no Magnitude band")
```

This checks only whether the rung's NAME appears anywhere in the charter text, never whether a
Magnitude band is actually missing near it. The docstring (lines 158-161) frames this as
"reported here so they stay visible instead of living in a conversation" — language implying a
live check of the actual condition. As written it is a static assertion: if the charter is later
edited to add e.g. "Supercluster: M11", this function keeps reporting "erratum (open)" forever,
because the rung's name is still present in the text — a check that cannot register its own
resolution. Everything else in `estate.py` is a genuine read-and-verify (JSON parses, files
exist, Ollama answers); this one function alone asserts a fact about content it never actually
inspects.

No other correctness issues found in `estate.py` — every exception handler in the file (checked
each one individually: lines 65, 84, 87, 90, 97, 101, 113, 183, 198, 239, 253, 284, 313, 315,
327, 336) genuinely records something (`silence.note` and/or the local `note()` helper carrying
`str(e)`/`type(e).__name__`), so this file has no silent handlers regardless of the S1 audit-tool
bug above. No caps found — `artifacts()` walks every file under every root with no sampling, per
Hard Rule 0.

---

## tuning.py (263 lines)

### T1. Known-open, confirmed still present: `regime()` is keyed off a 15-minute measured success rate, not quota/headroom — CONFIRMED

Now at `tuning.py:160-212` (`cloud_success_rate`, `regime`). `cloud_success_rate(minutes=15)`
reads `count(*)`/`sum(outcome='ok')` from `cascade_scratch.db`'s `usage` table over the trailing
15 minutes; `regime()` requires `n >= CLOUD_MIN_BUCKETS` (3) AND, once `calls >= 20`, that this
measured rate clears `CLOUD_MIN_SUCCESS` (0.35) before calling the pool "cloud." Unchanged from
the prior finding.

**New, directly relevant to the priority trace above:** because P1 establishes that nearly all
live traffic is concentrated on 1-2 top-ranked buckets, the `usage` table this function reads is
itself dominated by those same 1-2 buckets' outcomes — the 15-minute success rate `regime()`
computes is not really "the pool's" success rate, it is close to "nvidia:free and gemini's"
success rate. If either of those two has a rough quarter-hour (a burst of 429s before its own
bench engages), `regime()` can plausibly read the whole pool as failing/local/starved while
27 fully healthy, completely untried buckets sit behind it — the measurement and the claim
mechanism share the same narrow aperture. SUSPECTED (follows from tracing the two files
together; not independently confirmed against a live `usage` table this session).

No caps, no two-writer violations, no silent handlers found in `tuning.py` (all 4 exception
handlers — lines 123, 133, 150, 183 — call `silence.note`).

---

## style_audit.py (211 lines)

### ST1. Known-open, confirmed still present: `TURN_ENDING` uses `re.M`, so `$` matches every internal line break — CONFIRMED

`style_audit.py:38-39`:

```python
TURN_ENDING = re.compile(
    r"(?:\.|\?)\s+(?:And|But|Yet|Still|Which|That)\b[^.]{0,80}\.\s*$", re.M)
```

With `re.MULTILINE`, `$` matches immediately before ANY `\n` in the string, not only at the true
end. `record_of()` (lines 48-51) returns the full multi-paragraph "Record" body via a `re.S`
lazy match, which routinely contains internal newlines between paragraphs. `TURN_ENDING.search(r)`
therefore fires if ANY internal line — not necessarily the record's actual final sentence — ends
on a turn-word-led clause, inflating `turn_endings`/`turn_rate` in `audit()`/`report()`
(lines 113-114, 168-169) beyond what "how often does this entry actually END on a turn" means.

### ST2. Known-open, confirmed still present: `main()` always exits 0 outside `--self-test` — CONFIRMED

`style_audit.py:195-207`. The non-self-test path calls `report(audit(texts))` and unconditionally
`return 0`, regardless of any `OVERUSED`/`OVER` flags `report()` printed (opening-shape overuse,
banned-tell overuse, em-dash density, turn-rate). A CI/automation caller checking the exit code
never sees a failure, even when every printed threshold is red. The `--self-test` path
(line 193) DOES correctly return 1 on failure, and `silence.py`'s own `main()`
(`silence.py:182`, `return 1 if silent else 0`) shows the pattern is known elsewhere in this
batch and simply not applied here.

### ST3. `report()`'s `most_common(N)` / slice truncation — SUSPECTED, borderline, flagged per this sweep's explicit instruction to treat `most_common(N)` as a Rule-0 candidate even when it looks reasonable

`style_audit.py:143` (`most_common(top)`, top=8), `:157` (`sorted(...)[:14]`), `:172`
(`most_common(10)`). All three limit only the PRINTED report — `audit()` itself
(lines 104-133) never samples or caps the corpus; every entry, every opener, every banned-tell
occurrence, and the full vocabulary Counter are computed over the complete input with nothing
dropped. Framing this as a question rather than a finding of data loss: no entity/roster/record
is silently excluded from processing or from the underlying data structures — only from a
human-readable top-N console summary of numbers that are already fully computed. Given the
project's Hard Rule 0 is about the LIBRARY silently deciding a smaller universe exists, and this
is a diagnostic report rather than the library's own output, this reads as plausibly fine
design — but the sweep instructions call out `most_common(N)` by name as a pattern to always
surface, so it's recorded here for the owner to rule on rather than silently passed over.

No caps, no shared-state writes, no two-writer issues elsewhere in this file. The `[◈◈]` regex
character class at `style_audit.py:44` contains the same Unicode codepoint (U+25C8) twice —
functionally a no-op duplicate, cosmetic only, not a behavioural bug (verified both characters
are byte-identical).

---

## scale_theories.py (148 lines)

Grepped the whole `src/` tree: none of `bulk_export_beta`, `growth_strike`,
`penetration_pressure`, or `surviving_theory` are called anywhere in the live pipeline. The
module's name appears exactly once elsewhere, in `derivation.py`'s `SCAN_MODULES` list
(`derivation.py:476-477`), which only scans it for module-level UPPERCASE physics constants — it
does not exercise any of the functions below. Findings here are therefore currently dormant.

### SC1. `bulk_export_beta()`'s degenerate-input branch silently floors to the baseline cost — SUSPECTED, LOW, dormant

`scale_theories.py:104-118`:

```python
def bulk_export_beta(mass_kg, resident_mass_kg=1e-3):
    if resident_mass_kg <= 0 or mass_kg <= resident_mass_kg:
        return 64.0
    return round(64.0 + math.log2(mass_kg / resident_mass_kg), 2)
```

When `mass_kg <= resident_mass_kg` — e.g. arguments passed in swapped order, or the function
called for a growth/import scenario where more mass ends up resident than the reference value —
the function returns the bare structural floor (64.0 exception bits) rather than raising or
otherwise signalling that the inputs describe something other than the shrink/export case the
formula was derived for. No live caller currently exists to trigger this, so real-world impact
is nil today; flagged because the shape (a default that quietly returns a plausible-looking
minimum instead of surfacing an unexpected argument order) is exactly the "default that hides an
error" pattern this sweep is asked to find, and this module is one call site away from being
wired into `assay`/`derivation` scoring, where a silently-too-low beta would understate a
theory's true exception cost.

No other issues found — `growth_strike()` and `penetration_pressure()` both guard their
divisions (`max(growth_time_s, 1e-6)`, `max(contact_area_m2, 1e-30)`), `surviving_theory()`'s
filter correctly matches exactly one entry (`T3_BULK_EXPORT`, the only `falsified_by` starting
with "Nothing attested"). No file I/O, no caps, no shared state in this module at all.
