# AUDIT — batch 08

Files: `src/cascade_bridge.py`, `src/completeness.py`, `src/pick_model.py`, `src/tuning.py`,
`src/catalogue_codex.py`, `src/sweep_plan.py`

Every line of every file in this batch was read in full. Findings below are grouped per module.

---

## src/cascade_bridge.py

This file was edited minutes before this audit (new `named_transient()`, `pool_exhausted()`,
`_TRANSIENT_WORDS`, `_TRANSIENT_CODES`, `_MULTI_CANDIDATE`, and the new dispositioning branch in
`_ask_call`). Reviewed adversarially per the brief.

### FINDING 1 (real, verified) — the unwrap step can destroy the signal `pool_exhausted()` and
the permanent-refusal classifier need, before either gets to see it

`cascade_bridge.py:814-850`:

```python
err = (box.get("error") or "").lower()
...
if pinned and any(w in err for w in _WRAPPERS):
    deeper = provider_error(pinned.bucket).lower()
    if deeper:
        err = deeper
permanent_words = ("authentication", "invalid_api_key", "credentials",
                   "insufficient balance", "no resource package",
                   "payment required", "needs billing", "depleted")
if pinned and (re.search(r"\b(401|402|403)\b", err)
               or any(w in err for w in permanent_words)):
    _bury(pinned.bucket, AUTH_BENCH)
elif pinned and (named_transient(err) or pool_exhausted(err)):
    pass
elif pinned:
    record_unrecognised(pinned.bucket, err or box.get("error") or "")
```

`_WRAPPERS = ("candidates failed", "every model in this pool")` (line 336) matches BOTH the
single-candidate case (`All 1 candidates failed: ...`) and the multi-candidate case (`All 11
candidates failed: ...`), and also `"every model in this pool is rate limited or unconfigured"`.
All three are pool-level aggregate statements, not statements about the specific pinned bucket.

The unwrap step (820-823) fires for all three, and calls `provider_error(pinned.bucket)` —
which reads the PINNED bucket's own last-error row, aged ≤180s. The file's own extensive
commentary at lines 376-394 argues this "cannot work by construction" for the multi-candidate
case because the pinned bucket may not even be one of the failed candidates — but that argument
only holds if `provider_error()` reliably returns `""` (stale/absent) for the pinned bucket in
that situation. Nothing in the code enforces that: if the pinned bucket happens to have ANY
fresh (≤180s) row in `bucket_state` — e.g. because a concurrent worker or a prior unrelated call
on that same bucket recorded an error moments earlier — `deeper` is truthy and **overwrites**
`err`, permanently discarding the "All N candidates failed" / "every model in this pool..." text
before `pool_exhausted(err)` or `named_transient(err)` (called on the *post-unwrap* `err` at line
830) ever see it.

Consequences, all downstream of the same root cause:
- `pool_exhausted()` can false-negative on a genuine multi-candidate pool exhaustion (the "All N
  candidates failed" phrase it pattern-matches is gone), sending a case the file's own comment
  says must never reach `record_unrecognised` (lines 384-388, "a category error") into the
  ledger anyway.
- Worse: if the substituted `deeper` text (the pinned bucket's own unrelated last error) happens
  to contain a 401/402/403 code or one of `permanent_words`, the pinned bucket gets buried for
  `AUTH_BENCH` (4 hours) based on a POOL-level aggregate failure that structurally may not even
  be about that bucket — reintroducing, inside the new code, the exact "provider_error() reads
  the PINNED bucket's row, but the call wasn't necessarily an attempt on that bucket" bug the
  same comment block describes being found and fixed in a different context (m108).

This is a genuine ordering bug: `pool_exhausted()` needs to see the ORIGINAL aggregate text, but
the unwrap happens first and unconditionally for anything matching `_WRAPPERS`, with no
carve-out for the multi-candidate/every-model-in-pool cases the file's own comments say should
be exempted from unwrapping. **VERIFIED** by tracing the exact code path; not exercised against
live traffic, so frequency is unknown, but the mechanism is real and doesn't depend on any
implausible timing — just a fresh (≤180s) `bucket_state` row for the pinned bucket, which is a
normal thing to have under sustained concurrent load (the exact scenario this file exists to
handle).

### FINDING 2 (real, verified, lower severity) — `named_transient`'s unbounded-substring word
list can silently swallow a genuinely unknown failure out of the investigation ledger

`cascade_bridge.py:368-373`:
```python
_TRANSIENT_WORDS = (
    "rate limit", "rate-limit", "rate_limit", "ratelimit", "too many requests",
    "quota", "throttl", "overloaded", "capacity", "high demand", "try again",
    "temporarily", "timed out", "timeout", "could not resolve host",
    "connection", "unconfigured", "service unavailable", "bad gateway",
)
```
Unlike `_TRANSIENT_CODES` (numeric codes, deliberately `\b`-bounded per the comment at lines
365-367 "so a classifier that cries wolf on a trace hash is worse than one that stays quiet"),
these words are matched as plain substrings with no word boundary. `"connection"` and
`"capacity"` in particular are short, common English word-fragments that can appear inside an
error string that is not actually reporting transient contention (e.g. a message that happens to
contain "...connection was terminated..." for a non-transient reason, or "incapacity"). Because
neither the `named_transient` branch nor the `pool_exhausted` branch bench the bucket (line
830-837, deliberate — "whether a refusal should also cost the bucket anything is an open owner
question"), the practical effect of a false-positive match here isn't a wrongful bench; it's that
a failure that should have gone to `record_unrecognised` (and thus to the owner's "immediately
investigate" ruling, line 453) is silently classified as an already-known throttle and never
recorded at all. This is a real, traceable risk given the plain-substring matching, though I
have no evidence of it having fired incorrectly yet — **VERIFIED** as a mechanism, frequency
**UNVERIFIED**.

### Confirmed correct (per the audit brief's specific questions)

- **Permanent-vs-transient ordering is correct.** The permanent classifier (`if` at line
  827) is checked before the transient/pool-exhausted classifier (`elif` at line 830), so a
  message containing both a permanent marker (e.g. "insufficient balance") and a transient word
  (e.g. "try again") is still correctly buried for `AUTH_BENCH`, matching the docstring's claim
  at `named_transient`'s line 412 ("Checked AFTER the permanent classifier..."). Traced and
  confirmed. **VERIFIED, no bug.**
- **`pool_exhausted()`'s regex is correct on the boundary case.** `_MULTI_CANDIDATE =
  re.compile(r"\ball (\d+) candidates failed\b")` (line 395) captures the numeral and
  `pool_exhausted()` (line 398-401) only returns `True` when `int(m.group(1)) > 1`. Traced
  `"All 1 candidates failed"` → group="1" → not >1 → `False` (correctly stays unrecognised, per
  the file's own stated intent at lines 390-394); `"All 11 candidates failed"` → group="11" → 11
  > 1 → `True`. **VERIFIED, no bug.**

### Minor / cosmetic (not flagged as primary findings, noted for completeness)

- Several `silence.note(...)` labels carry stale line numbers that no longer match their call
  site (e.g. `cascade_bridge.py:137` calls `silence.note("cascade_bridge.py:100")`;
  `cascade_bridge.py:151` calls `silence.note("cascade_bridge.py:113")`;
  `cascade_bridge.py:753` calls `silence.note("cascade_bridge.py:151")`). Purely cosmetic —
  doesn't change behavior — but misleads anyone using the silence log to find the actual call
  site.
- `dead_forever()`'s permanent-verdict code list (line 320: `("401", "402", "404", "410")`)
  omits `403`, while the runtime classifier in `_ask_call` (line 827) treats 403 as permanent.
  These operate on different data sources (`POOL_PROOF.json` verdict strings vs. live call error
  text) so this may be intentional, but it's an inconsistency between the file's two
  "permanent failure" classifiers worth the owner's eye. **UNVERIFIED** as a live bug.

---

## src/completeness.py

### Confirming the already-filed finding — VERIFIED, real

`completeness.py:71-119`, specifically the cache path in `category_size_probe` (93-118): the
module-level `_CS_CACHE["d"]` dict is returned BY REFERENCE from `_cs_load()` (not a copy), and
`category_size_probe` — called from inside `audit()`'s `work()` closure, which runs under
`ThreadPoolExecutor(max_workers=workers)` (default 6, line 211/333) — both mutates it
(`cache[k] = {...}`, line 111) and serializes it (`json.dump(cache, f)`, line 115) with **no
lock**. Multiple worker threads can be inside this block simultaneously (`audit()` runs 8
category probes per source across `workers` concurrent sources), so one thread's `json.dump`
iterating `cache.items()` while another thread does `cache[k] = ...` for a different key is a
live `RuntimeError: dictionary changed size during iteration` risk. **CONFIRMED.**

### Related finding, not previously filed — fixed temp-file name shared across the same
concurrent workers (VERIFIED)

`completeness.py:110-118`:
```python
cache = _cs_load()
cache[k] = {"at": time.time(), "n": got}
try:
    tmp = _CS_CACHE_P + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f)
    silence.replace_retry(tmp, _CS_CACHE_P)
except Exception:
    silence.note("completeness.py:cs-cache")
```
The temp filename is a **fixed** path (`_CS_CACHE_P + ".tmp"`), not unique per thread/pid. This
is the exact anti-pattern `cascade_bridge.py`'s `record_unrecognised` was rewritten to avoid (see
that file's comment at lines 484-490: "The pid+thread-unique name makes that unavailable to get
wrong" — written in the same project, same day). Here it's still present: up to 6
`ThreadPoolExecutor` workers can each independently `open(tmp, "w")` (truncating), `json.dump`,
and `replace_retry` on the **identical** tmp path with no lock guarding the sequence. Two
threads racing here can (a) interleave writes into the same tmp file, producing a
corrupted/mixed body that gets renamed over the good cache, or (b) simply lose updates —
whichever thread's `replace_retry` lands last wins, silently discarding the cache entries other
threads wrote to their own (by-reference-shared, but time-of-open-differs) copies. The final
rename via `silence.replace_retry` is atomic for THAT call, but doesn't fix the shared-tmp-name
collision leading into it. **VERIFIED** by code trace; same root cause as Finding 1's dict
(shared mutable state with no lock across `ThreadPoolExecutor` workers), but a distinct failure
mode (file corruption / lost cache updates vs. process-crashing `RuntimeError`).

### Everything else in this module — reviewed, no further findings

`land()`'s three-layer guard (empty-result refusal, shrink-floor refusal, `replace_retry`
truthiness check) is correct and consistent with the two-writer/atomicity contract — it uses
`silence.replace_retry` for the actual landing, and the `--only` exemption is correctly
one-directional (never lands a filtered slice over the full corpus). `host_reachable()`'s
module-level `_REACH` dict is also touched by the same worker threads without a lock, but plain
dict `__setitem__`/`__getitem__` is fine under the GIL for this usage (no iteration-while-mutated
hazard, at worst a redundant duplicate probe) — not flagged. `--top` in `main()` only bounds what
is PRINTED to the console; the code explicitly documents and honors "the file always holds every
row" (line 415, 440-441) — correctly NOT a Hard Rule 0 violation.

---

## src/pick_model.py

**CLEAN.** Read in full; no correctness bugs, no swallowed-failure issues, no cap violations, no
two-writer-contract violations found.

Specifically checked and confirmed correct:
- `FAMILY_TIERS` substring matching is tier-ordered (tier 5 checked before tier 1) so
  `"qwen3"`/`"qwen2.5"` correctly outrank the generic `"qwen"` catch-all regardless of intra-tier
  list order (since same-tier order doesn't change the returned score anyway).
- `resident()` correctly applies no MoE exemption (per the "STILL DISQUALIFYING" comment at
  lines 79-83, 85-91) — traced, matches.
- `save_config()` correctly discards no boolean: both the "no `model:` line matched" case (line
  120-123) and the `replace_retry` denial case (line 129-133) return `False` and are checked by
  the caller (`main()`, line 346), matching the docstring's claim about the two historical bugs
  it fixed.
- Minor cosmetic only: `silence.note("pick_model.py:150")` at line 211 no longer matches its
  actual line number (same class of stale-label issue as noted in cascade_bridge.py). Not a
  functional bug.

---

## src/tuning.py

**CLEAN.** Read in full; no correctness bugs found.

Specifically checked and confirmed correct:
- The "ZERO IS A REQUEST" fix in `workers()` (line 226-244): `min(requested, n) if requested is
  not None else n` — traced with `requested=0`: `0 is not None` is `True`, so `min(0, n)` = `0`,
  correctly honoring a caller's explicit request for zero workers rather than falling through to
  the full profile count. Matches the docstring's claim.
- `regime()`'s cloud/local/starved decision logic (188-212) correctly requires both bucket count
  AND (when enough calls exist to judge) a measured success rate ≥ `CLOUD_MIN_SUCCESS`, with the
  "not enough data yet" case correctly not vetoing cloud (matches the stated m59/M8/m66 lesson
  about certifying capacity vs. reachability).
- `_CACHE` (module dict) is read/updated without a lock across potential concurrent callers of
  `regime()`, but the worst case is redundant recomputation (extra file/DB reads), not
  corruption — not flagged as a defect.

---

## src/catalogue_codex.py

### FINDING 1 (verified against real data) — 70 codex elements silently miscategorized via the
default-category fallback

`catalogue_codex.py:159`: `"category": TYPE_CATEGORY.get(etype.lower(), THINGS)`.

Ran `parse_codex()` against the real
`C:/Users/imarl/Documents/5e Character Builder/custom/THE_PRIME_OMNIVERSE_CODEX.md` and checked
every element type against `TYPE_CATEGORY` (lines 54-67). Three element types are NOT in the
dict and silently fall back to `THINGS` (Vessels & Things) with no warning:

```
weapon property     35 occurrences   e.g. "Ammunition", "Burst Fire", "Special (Double-Bladed Scimitar)"
race variant        28 occurrences   e.g. "Mark of Detection", "Mark of Finding", "Mark of Handling"
background variant   7 occurrences   e.g. "Variant Criminal: Spy", "Variant Entertainer: Gladiator"
```

By analogy to sibling entries already in `TYPE_CATEGORY` these are miscategorized: `"race variant"`
items are Eberron Dragonmarks (Mark of Detection/Finding/Handling), and the dict already maps
`"dragonmark": POWERS` — so these are magic-system entries being filed as physical Things.
`"weapon property"` (Ammunition, Burst Fire) are rules describing how a weapon behaves, not
physical items — closer to `"racial trait": POWERS` / `"rule": POWERS` than to `"weapon": THINGS`.
`"background variant"` items are background-feature variants, and `"background": POWERS` /
`"background feature": POWERS` are already mapped — these should follow suit, not fall to THINGS.
**VERIFIED** — 70 real catalogue entries land under the wrong top-level shelving category with no
signal to a human that the mapping was a guess.

### FINDING 2 (verified) — unguarded read-modify-write on `data/SWEEP_ROLL.json`, a file the code
itself documents as multi-writer

`catalogue_codex.py:122-123` (read), `196-197` (in-memory mutation inside the write loop),
`203` (write):
```python
with open(ROLL, encoding="utf-8") as f:
    roll = json.load(f)
...
    r["entry_count"] = len(rec["entries"])
    r["status"] = "catalogued"
...
if not args.dry_run and written:
    # ATOMIC: ... Four scripts write this roll. Fixed 2026-08-25.
    silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)
```
The comment at line 200-202 explicitly acknowledges "Four scripts write this roll" and that the
prior bug was a non-atomic write ("an interrupted write here kills the next run of either script
outright"). That half is now fixed — `silence.write_json` prevents a TORN write. But the other
half of the multi-writer hazard is still present: this script reads the WHOLE roll once at
start, and near the end of a run that may take a while (it fetches/joins register text for every
element of every matched section) writes back the WHOLE in-memory `roll` object, with no lock
and no re-read/merge before landing. If any of the other three scripts documented as writers of
this same file commits a change to `SWEEP_ROLL.json` between this script's read (line 122) and
write (line 203) — for example marking a different source's `entry_count`/`status` — that write
is silently clobbered: this script's stale in-memory copy overwrites it wholesale. `silence.write_json`
guarantees the bytes that land are not torn; it does not guarantee they're not a stale
snapshot. **VERIFIED** as a structural race, matching lens item 5 (concurrency races) exactly —
unguarded read-modify-write on a shared file touched by more than one process.

### Checked, not currently manifesting (low priority, noted for completeness)

Fuzzy section-matching (`main()`, lines 130-137: bidirectional substring match, first-match-wins
in dict insertion order, no longest-match tiebreak — unlike `completeness.py`'s analogous
primary-source matcher, which explicitly does longest-match). Ran it against the real
`SWEEP_ROLL.json` + parsed codex: 6 roll entries need matching, 2 matched, **0 ambiguous**
(no roll entry currently has more than one candidate section). Structurally fragile compared to
the longest-match pattern used elsewhere in this codebase, but **not presently causing any
misattribution** with the current data. Noted as a latent risk, not a live bug.

---

## src/sweep_plan.py

### FINDING 1 (verified, high confidence, may be live in THIS sweep run) — `record()`'s
serialization only protects against other THREADS in the same process; the sweep's real
concurrency is separate PROCESSES, which the lock does nothing to serialize

`sweep_plan.py:81-113`:
```python
_RECORD_LOCK = threading.Lock()

def record(run, covered):
    """... SERIALISED, because the whole point of this file is that sixteen batches run AT ONCE
    and each one reports its own coverage. ... The lock covers this process; the atomic land
    covers a torn read. ..."""
    with _RECORD_LOCK:
        try:
            with open(COVERAGE, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        ...
        for m in covered:
            data[m] = {"run": run, "at": now}
        try:
            import silence
            silence.write_json(COVERAGE, data, indent=1, sort_keys=True)
        except Exception:
            ...
        return data
```
`_RECORD_LOCK` is a `threading.Lock` — a per-process, in-memory primitive. It provides zero
mutual exclusion between separate OS processes. The docstring's own architecture claim ("sixteen
batches run AT ONCE and each one reports its own coverage") plus this very audit's assigned
closing step — invoking `sweep_plan.record(...)` via a brand-new `python.exe -c "..."`
subprocess, once per batch/agent — confirms the 16 batches call `record()` from **16 separate
processes**, not 16 threads inside one process. A `threading.Lock` cannot serialize that.

The docstring explicitly says this fixes a "found by the sweep auditing this very file" bug:
"two batches reading the same file, each adding its own modules, each writing back its own copy
— and the loser's modules vanish from the record." That failure mode is a classic lost-update
race (read-modify-write without a cross-process lock), and it is **not actually fixed** by this
code for the real usage pattern: two separate processes can both `open(COVERAGE)` and read the
same snapshot before either writes, each add their own batch's modules to their own in-memory
`data`, and whichever calls `silence.write_json` LAST wins — silently discarding the other
process's coverage additions, even though neither individual write is torn. Only the torn-write
half of the original bug is fixed; the interleaved-read half is not, because the fix (a
`threading.Lock`) doesn't reach across process boundaries. **VERIFIED** by tracing the exact
mechanism and cross-checking it against this audit's own invocation pattern (16 parallel agents,
each closing with its own `python.exe -c "sweep_plan.record(...)"` call) — this is a structural
gap, not a hypothetical one, and it directly undermines `missing()`'s stated purpose ("the proof
that a sweep was complete, or the list of what it silently skipped").

A real fix needs cross-process mutual exclusion (an OS-level file lock around the
read-modify-write, or a merge-safe write such as reading fresh immediately before writing inside
a filesystem lock, or moving to a design where each batch writes its own file and a separate
reducer merges them).

### Everything else in this module — reviewed, no further findings

`modules()`/`batches()`/`missing()` correctly enumerate every `.py` file in `src/` with no
truncation (Hard Rule 0 compliant — this file's entire purpose is enforcing exactly that), and
the "unreadable file" handling (lines 47-60) correctly avoids the old silent-zero-lines bug by
marking `unreadable: True` rather than defaulting to `lines: 0` unflagged.
