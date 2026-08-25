# AUDIT — Batch 07 (Sweep run #25)

Files: `src/cascade_bridge.py`, `src/allsweep.py`, `src/estate.py`, `src/backfill.py`,
`src/catalogue_codex.py`, `src/scope.py`. Every line of every file was read. Where a hypothesis
could be tested, it was — either against real live data files (`state/POOL_UNRECOGNISED.json`,
`data/SWEEP_ROLL.json`) or with a runnable reproduction against `pipeline.py`'s real functions.

---

## PART 1 — cascade_bridge.py: the classifier map, and (a)-(d)

### (a) The full classifier

`_ask_call`'s failure branch (fires only when `box["failed"]` is True, i.e. the stream reported
a `type:"error"` event or raised — a **separate** path is the deadline/timeout branch, which
never reaches the text classifier at all):

| Disposition | Exact predicate | Effect |
|---|---|---|
| **deadline/no-answer** | `not finished` (from `done.wait(timeout)`) — no text classifier involved | `_bury(pinned.bucket)` (graded exponential bench, `FIRST_BENCH=60`→`MAX_BENCH=900`s) |
| **auth-bench (permanent-ish)** | `pinned and not exhausted and (re.search(r"\b(401\|402\|403)\b", err) or any(w in err for w in permanent_words))` where `permanent_words = ("authentication","invalid_api_key","credentials","insufficient balance","no resource package","payment required","needs billing","depleted")` (:870-875) | `_bury(pinned.bucket, AUTH_BENCH)` = 4h bench |
| **pool_exhausted** | `pool_exhausted(err)`: `_MULTI_CANDIDATE = re.compile(r"\ball (\d+) candidates failed\b")`, true when the captured N > 1 (:403-409) | falls into `elif pinned and (exhausted or named_transient(err)): pass` — no bench, no ledger row (already counted by throughput/`usage.outcome`) |
| **named_transient** | `_TRANSIENT_CODES.search(e)` (`\b(408\|409\|425\|429\|500\|502\|503\|504)\b`) or any phrase in `_TRANSIENT_WORDS` (rate limit, quota, throttl, overloaded, timeout, could not connect, unconfigured, service unavailable, bad gateway, …) (:412-425) | same as above — pass, no ledger row |
| **dead_forever** (a separate, permanent, proof-driven list — not part of the per-call text classifier) | `POOL_PROOF.json` row whose `verdict` contains `401`/`402`/`404`/`410`, or the phrases `"no such model"`/`"needs billing"`/`"bad key"`, and the proof file is ≤`PROOF_TTL`=3600s old (:290-327) | excluded from `_alive()`/candidate selection entirely |
| **unrecognised** | everything else that reaches the `elif pinned:` fall-through (:884-896) | `record_unrecognised(pinned.bucket, err or box.get("error") or "")` — written to `state/POOL_UNRECOGNISED.json`, surfaced by the `every pool failure is recognised` standard |

`unrecognised_open()` (:504-543) then **re-triages on read** (m118, run #24's edit): drops any
row whose `error` now matches `pool_exhausted()` or `named_transient()`, even if it was written
under an older classifier version. VERIFIED — this is the correct, currently-working behaviour;
see part (c) below for the limit of what re-triage catches.

### (b) The "no answer text produced" / "empty response" rows — is there a predicate?

**No.** Both phrases are the EXACT strings Cascade's own engine writes via
`self.router.record_failure(model, "no answer text produced", cooldown=60)`
(`C:\Users\imarl\cascade\cascade\engine.py:343`) and
`self.router.record_failure(model, "empty response", cooldown=60)` (`engine.py:277`) — VERIFIED
by reading both call sites. Neither string, nor any substring of it ("no answer", "empty
response", "produced no", "blank reply"), appears anywhere in `_TRANSIENT_WORDS`,
`permanent_words`, or `_WRAPPERS` in `cascade_bridge.py`. **This is deliberate and correct as
designed** — the file's own :339-403 comment block names `groq:groq/compound-mini: empty
response` as *the* worked example of the one genuine unknown the ledger exists to protect. So
today: no existing disposition fits it (it is neither an auth failure, nor a rate limit/timeout,
nor a multi-candidate pool-dry signal — it is a *successful* HTTP response carrying zero
content), and it correctly falls through to `record_unrecognised`.

**But it is now recurring under two DIFFERENT phrasings**, and `record_unrecognised`'s dedup key
is `bucket + "|" + text[:80]` (:476) — an exact-text key. `no answer text produced` and `empty
response` are two distinct English descriptions of the identical failure mode (an engine
`record_failure` call for zero output), fired from two different code paths in the SAME upstream
function (`engine.py:277` after a tool-call turn produced nothing; `engine.py:343` after a
non-tool turn produced nothing). They will never merge into one ledger row, no matter how many
times either recurs, because the key is textual not semantic.

**Minimal, honest predicate**, if this is to be promoted out of "unrecognised": an
**exact-phrase match anchored to the two known Cascade wordings**, not a broad substring:

```python
_EMPTY_CONTENT = ("no answer text produced", "empty response")

def empty_content(err):
    e = (err or "").lower().strip()
    return e in _EMPTY_CONTENT
```
(`==`/`in` against the whole normalised string, not `w in err`, since a bare `"empty" in err` or
`"no answer" in err` would swallow unrelated genuinely-unknown messages that happen to contain
those common words — exactly the over-matching failure mode the file's own `_TRANSIENT_WORDS`
comment warns about for `"connection"`/`"capacity"`.)

**Which disposition does it belong in?** Neither existing bucket is honest. It is not
`named_transient` in the router-policy sense — nothing here has established that retrying gets
different content (unlike a 429, which is definitionally retryable), and folding it into
`named_transient` would make it invisible in the one place (the ledger) that is currently
tracking it as a real, recorded oddity. It is not an auth/permanent fault either — the key
works, the bucket answers. **It needs its own named disposition** — a `empty_content` bucket
that is *recorded but not benched* (mirroring `named_transient`'s "recognised, deliberately not
routing-punished" stance until the owner rules on routing question B), so the two rows collapse
under one classification and stop reading as "the one true unknown fault" when it is actually a
recurring, nameable Cascade behaviour. UNVERIFIED as a prescription (this is a design
recommendation, not a bug fix); VERIFIED that no current predicate matches either phrase.

### (c) The case discrepancy in the 11 `All 1 candidates failed` rows

Read live from `state/POOL_UNRECOGNISED.json` (VERIFIED, not inferred):

```
groq:openai/gpt-oss-20b          02:31:19  All 1 candidates failed: Llama 3.3 70B (Groq)
groq:openai/gpt-oss-120b         02:31→02:43  All 1 candidates failed: GPT-OSS 120B (Groq)
cloudflare:free                  02:31→02:43  All 1 candidates failed: Qwen2.5 Coder 32B (Cloudflare)
cohere:free                      02:31→02:43  All 1 candidates failed: Command R+ (Cohere)
groq:groq/compound-mini          02:31→02:43  All 1 candidates failed: Llama 3.1 8B (Groq)
groq:qwen/qwen3.6-27b            02:43:58  All 1 candidates failed: Qwen 3.6 27B (Groq)
hyperbolic:free                  02:31→02:43  All 1 candidates failed: Qwen2.5 72B (Hyperbolic)
openrouter:free                  02:32→02:44  All 1 candidates failed: Nemotron 3 Ultra 550B
sambanova:free                   02:32→02:44  All 1 candidates failed: DeepSeek V3 (SambaNova)
zai:free                         02:32→02:44  All 1 candidates failed: GLM 4.7 Flash (Z.AI)
gemini:models/gemini-2.5-flash   03:30:11  all 1 candidates failed: llama 3.3 70b (groq)      <- lowercase
gemini:models/gemini-2.5-flash   05:27:40  all 1 candidates failed: llama 3.1 8b (groq)       <- lowercase (NEW, appeared mid-audit)
```

**All ten title-case rows were written between 02:31:12 and 02:44:02, in a single ~13-minute
burst, and NONE has recurred since** (their `last_seen` is frozen 2.7-3h before this audit ran).
**Both lowercase rows are for the `gemini:...` bucket, one at 03:30:11 and one at 05:27:40 —
the second one landed 17 seconds before I queried the file, i.e. the lowercasing code is live
and firing right now.**

Read at source: `cascade_bridge.py:845` — `err = (box.get("error") or "").lower()` —
unconditionally lowercases before any classification, and every reassignment of `err`
downstream (`deeper = provider_error(pinned.bucket).lower()` at :867) is also lowered. There is
**no second write path** inside `_ask_call`'s failure branch; the fallback
`record_unrecognised(pinned.bucket, err or box.get("error") or "")` at :896 can only ever reach
`box.get("error")` (original case) when `err` is falsy, and `err` can only be falsy when
`box["error"]` was itself empty — so that branch is dead for real content (VERIFIED by tracing:
`.lower()` of any non-empty string is never `""`). **So under the code as it stands, this call
site is incapable of writing anything but lowercase.**

**Conclusion: the ten title-case rows are fossils from a superseded code version.** They were
all written in the 02:31-02:44 burst, which is *before* `HANDOFF.md`'s own account of Run #23
(03:20-04:1x) building `named_transient()`/`pool_exhausted()`/the unwrap-before-classify fix —
the exact machinery this call site now runs. The first lowercase row appears at 03:30:11,
essentially the moment Run #23's window opens. The lowercasing is very likely a side effect of
that session's rewrite of the classify-then-record logic (the file's own comment nearby says
"Matching is case-folded because providers do not agree on capitalisation" — case-folding was
added for *matching* robustness, and using the same `err` variable for the eventual `record_
unrecognised` call carried that fold into the STORED text as a side effect). **The ten old rows
are not being refreshed by anything currently running** — they sit in the ledger, still inside
`unrecognised_open()`'s 24h window, still failing to match `pool_exhausted`/`named_transient` (by
design, since `All 1 candidates failed` deliberately stays unrecognised), and so they read on the
standards page as "currently open, currently unexplained" when they are in fact **3-hour-old
fossils from a code generation that predates the classifier rewrite that would have handled
them differently** — no live process has revisited whether they'd still occur under current code.
This is the same shape as NEXT_STEPS lesson 8 ("age every row and read the text") but from a
new angle: **the case of the text is itself evidence of which code version wrote it, and nothing
currently reads that signal.** VERIFIED (live ledger + file mtime + HANDOFF.md's own timeline
cross-checked; the mechanism by which the case changed is the strongest available inference,
marked UNVERIFIED as a precise causal claim about which commit introduced it, since there is no
git history in this repo to pin it to a specific edit).

One more confirmed fact along the way: `record_unrecognised(bucket, err)` itself does **no**
case-folding (verified by reading :458-501 — it stores `text` verbatim, whitespace-collapsed
only). The lowering is entirely the caller's habit at `_ask_call:845`, not a property of the
storage function. `verify_math.py:1538-1539` calls `record_unrecognised` directly with
mixed-case probe text (`"  HTTP 418   I am a   teapot  "`) against a *separate* test file, so it
does not pollute the real ledger, but it does prove the storage layer is case-agnostic by design
— any future direct caller of `record_unrecognised` could reintroduce case-mismatched fossils
the same way. UNVERIFIED as a live risk (no other caller exists today; confirmed by `grep`).

### (d) `gemini:models/gemini-2.5-flash | all 1 candidates failed: llama 3.3 70b (groq)`

**This is a real, structural bucket/model attribution defect, and it is exactly the mechanism
`cascade_bridge.py`'s own :384-390 comment already names for a different pin/label pair** ("pin
`groq:openai/gpt-oss-20b` against candidate label `Llama 3.3 70B (Groq)`"). Traced to source in
`C:\Users\imarl\cascade\cascade\router.py:327-338` (`Router.candidates`):

```python
def candidates(self, pool, pinned=None):
    if pinned:
        for model in self.models:
            if model.id == pinned:
                rest = self._order([m for m in self.models if m.id != pinned and pool in m.pools])
                ready, _ = self.provider_ready(model)
                return ([model] if ready and model.enabled else []) + rest
    return self._order([m for m in self.models if pool in m.pools])
```

**A "pin" is not exclusive.** `router.candidates(pool, pinned)` always appends the rest of the
pool as fallback candidates, and if the pinned model itself is not `provider_ready()` at that
instant (a router-side cooldown/rate-limit state that `cascade_bridge`'s own `_alive()`
bookkeeping does not see — they are two independent trackers), the pin is dropped entirely and
`candidates()` returns **only** `rest`. `engine.stream_chat` (`engine.py:180-183`) then tries
`candidates[:limit]` in order, appending each attempted model's *label* to `tried`, and on
exhaustion yields `"error": f"All {len(tried)} candidates failed: {', '.join(tried)}"`
(`engine.py:359-362`). If, at that moment, only one OTHER model in the whole pool happens to be
`_order()`-available (everything else mid-cooldown), `tried` ends up with exactly one entry —
**a completely different bucket's model** — producing "All 1 candidates failed: <unrelated
model>" while `cascade_bridge` still believes it reserved and is reporting on the bucket it
originally pinned.

Back in `cascade_bridge.py`, `pinned.bucket` (the bucket the bridge actually reserved, `gemini:
models/gemini-2.5-flash`) is what gets passed to `record_unrecognised` (:896), while `err` — the
STRING being recorded — names the Groq model the engine silently substituted. The deeper-unwrap
step (:865-869) tries `provider_error(pinned.bucket)`, which reads `bucket_state.last_error` for
the *gemini* bucket specifically — and finds nothing recent there, because the call never
actually touched Gemini's endpoint at all — so `err` stays as the raw wrapper text, and the row
lands under the wrong bucket key.

**Root cause is a mismatch between Cascade's contract and cascade_bridge's assumption.**
`cascade_bridge.py:398-402`'s own design rationale for keeping `All 1 candidates failed` loud
explicitly assumes "there the pin and the attempt do agree" — and this row is a live, verified
counterexample to that assumption, reached by a different road than the multi-candidate case
`pool_exhausted()` was built to catch. VERIFIED (traced through both `cascade_bridge.py` and
Cascade's live `router.py`/`engine.py` source, and cross-checked against the live ledger row and
its sibling case discrepancy above).

---

## PART 2 — new findings, other files

### `backfill.py:191` — VERIFIED, MAJOR. Every character backfill.py successfully finds is
silently discarded on write, whenever it actually adds one.

```python
    P.write_record(path, r)
```

`backfill_source()` appends newly-found characters directly onto `r["entries"]` (:176-190),
where `r` is the SAME record object loaded once at the top of `main()` via `P.records()`. It
then calls `pipeline.write_record(path, r)` — **the pipeline side of the two-writer contract**,
not `write_record_catalogue` — **the cast-growing side**, which is what this operation actually
is (backfill.py exists specifically to grow a source's cast, per its own docstring: "recover the
main casts the original cataloguing crawl missed").

`write_record` (`pipeline.py:503-537`) is built on the opposite authority assumption: "the
pipeline only ever changes per-entry judgment fields... every entry the disk version has that
this in-memory copy lacks is kept" (pipeline.py:513-514). When the in-memory entry count differs
from what's on disk, it takes **disk's entry list as the base** (`merged = disk`, :535) and only
copies a fixed set of judgment fields (`category`, `scale_note`, `magnitude`, `topic`,
`catalogued`, …) from matching-by-name `rec` entries onto it. **Entries that exist only in
`rec` — i.e. every entry backfill.py just added — have no match in `disk` and are never
appended.** The final write persists disk's original entry list, unchanged, while printing a
console message that says "merged".

**Reproduced directly** against the real `pipeline.write_record`:

```
disk (2 entries: Alice, Bob)  +  in-memory rec (3 entries: Alice, Bob, "Charlie (backfilled)")
  -> P.write_record(path, rec)
  -> console: "write_record: wr_test.json drifted on disk (3 -> 2 entries); merged"
  -> file on disk after write: ['Alice', 'Bob']   Charlie present? False
```

This fires on **every** non-dry, non-empty backfill run, because backfill always increases the
in-memory entry count relative to disk before writing — the drift-merge branch is guaranteed to
activate exactly when there is new data to save. The `--all` mode's printed "`added NNN`" counts
are real (the entries were built and appended in memory) but never survive to disk. This is the
single biggest defeat of this file's stated purpose, larger in effect than the already-known
subcategory-skip bug (`backfill.py:84-94`, `[KNOWN]`, unchanged from NEXT_STEPS.md §3 — the
top-level-≥40 short-circuit that skips the subcategory walk).

**Fix direction** (not applied — read-only audit): `backfill_source()` should call
`pipeline.write_record_catalogue(path, r)` instead, whose merge direction ("rec's entry LIST
wins... a merge never shrinks a cast", pipeline.py:419-421) matches what backfill.py is actually
doing.

### `backfill.py:132-154` — `[KNOWN]` roster() top-level-≥40 short-circuit skips subcategories.
Unchanged from NEXT_STEPS.md §3, re-confirmed by reading: `if len(out) < 40:` at :84 gates the
entire subcategory walk.

### `catalogue_codex.py:159` — `[KNOWN]` 70 codex elements miscategorised via the THINGS
fallback. Unchanged from NEXT_STEPS.md §3 (already verified against real data by a prior run).

### `catalogue_codex.py:203` — `[KNOWN]` (generalised in NEXT_STEPS.md §3's `silence.write_json`
return-value note) — `silence.write_json(ROLL, roll, ...)` return value is not checked; a
persistent-lock failure would report success while `SWEEP_ROLL.json` never lands.

### `catalogue_codex.py:130-136` — UNVERIFIED, minor, new. Loose substring section-matching.

```python
for k, t in sec_by_norm.items():
    if n and (n in k or k in n):
        title = t
        break
```

Matches a roll source name to a codex section by two-way substring containment, in dict
insertion order, with no scoring, no length-based disambiguation, and no protection against a
short name matching multiple sections. Ran this against the real `data/SWEEP_ROLL.json` and
`THE_PRIME_OMNIVERSE_CODEX.md` (VERIFIED the matching mechanism, not a live bug): today only 2
of 215 roll entries are unmatched-to-catalogued and route through this code, and both match
correctly (`the Witch Tradition` -> `Extras: The Witch Tradition`, a legitimate substring). No
live misattribution exists right now, but the mechanism has no safeguard if a future codex
section title happens to contain (or be contained by) an unrelated roll source's name.

### `catalogue_codex.py:75,195` — UNVERIFIED, minor, new. `slug()` truncates filenames to 60
characters with no collision check. Confirmed empirically no current collision among the 215
roll entries, but the longest current slug is exactly 60 characters (at the cap), so this is a
live-but-currently-silent latent risk: two long, similarly-prefixed source names could someday
truncate to the same slug and have their `write_record_catalogue` calls silently interleave
into one file.

### `scope.py:73-81` — `[KNOWN]`, Hard Rule 0. `srlimit=3` × 4 queries, then `titles[:8]`,
feeding the fiction-wide Magnitude ceiling. Unchanged from NEXT_STEPS.md §3 item F.

### `scope.py:102-120` — UNVERIFIED, minor, new. `build()` does an unguarded read-modify-write
on the shared `data/SCOPE.json`: reads the whole file, computes only the missing hosts, and
writes the merged dict back via `silence.write_json` (atomic write, but the read-compute-write
window itself is not locked). `scope.py` is in `allsweep.NEVER_RUN` (never auto-invoked) and is
a manual/rare operation, so the concurrency exposure is low, but if it is ever run twice
concurrently (e.g. two manual invocations, or a manual run overlapping a future automated one),
one process's newly-scoped hosts would be lost to the other's stale in-memory copy — the same
shape as the five already-known `SWEEP_ROLL.json` writers in NEXT_STEPS.md §3, not previously
named for `SCOPE.json` specifically.

---

## Modules read end to end and found CLEAN this run

- **`estate.py`** — pure read-only audit module, no writes anywhere in the file. Every file-type
  branch (`.json`, text extensions, `.py` via `ast.parse`) has its own narrow exception handling
  routed through `silence.note`, zero-byte logs are correctly exempted from the "corrupt" verdict,
  and every check (`charter`, `written`, `terminal`, `external`) degrades to a reported error
  rather than crashing or silently passing. Matches and reconfirms run #24's own "found CLEAN"
  listing for this module.
- **`allsweep.py`** — all three tiers (IMPORT, LINT, VERIFY) and every one of `reconcile()`'s
  seven independent try/except blocks correctly call `note()` on both success and failure; no
  swallowed exception is silent. `main()`'s `bad` count and exit code are consistent with what
  actually ran (quick mode correctly excludes tiers it skipped). The output write
  (`silence.write_json(OUT, ...)`) is correctly atomic. The one adjacent issue —
  `overwatch.py`'s reconcile-output *filter* dropping real findings before they reach WATCH.md —
  is already correctly attributed to `overwatch.py`, not this file, in NEXT_STEPS.md §3.

---

## Summary of severity

- **HIGH / new, VERIFIED:** `backfill.py:191` (wrong two-writer-contract function; every
  backfilled character is discarded on write when the run actually adds anything).
- **cascade_bridge.py (a)-(d), all VERIFIED against live data:**
  - (b) no predicate names the "empty response"/"no answer text produced" class; correctly falls
    to unrecognised today, but the two phrasings never merge into one row (exact-text dedup key).
  - (c) case split across the 11 "All 1 candidates failed" rows traced to a code-version
    boundary: 10 title-case fossils from before the current unconditional `.lower()` at
    `cascade_bridge.py:845`, 1(-now-2) lowercase rows from the current code, one of which was
    written 17 seconds before this audit queried the file.
  - (d) `gemini`-bucket row naming a Groq model traced to `Router.candidates()` in Cascade's own
    `router.py:327-338` treating a "pin" as a preference with full-pool fallback, not an
    exclusion — confirming the file's own stated assumption ("pin and attempt agree" for
    single-candidate rows) is false in this instance.
- **Minor/new, UNVERIFIED:** loose substring section-matching in `catalogue_codex.py:130-136`;
  60-char slug collision risk in `catalogue_codex.py:75`; unguarded read-modify-write on
  `scope.py`'s `SCOPE.json`.
- **KNOWN, re-confirmed, unchanged:** `backfill.py:84-94`, `catalogue_codex.py:159`,
  `catalogue_codex.py:203`, `scope.py:68-81`.
- **CLEAN:** `estate.py`, `allsweep.py`.
