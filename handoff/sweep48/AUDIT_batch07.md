# Sweep 48 — batch 07 audit

**Modules read (in full, no sampling):**

| module | lines read | total lines |
|---|---|---|
| src/cascade_bridge.py | 1-2256 | 2256 |
| src/corpus_db.py | 1-1032 | 1032 |
| src/identity.py | 1-753 | 753 |
| src/anchors.py | 1-577 | 577 |
| src/backfill.py | 1-475 | 475 |
| src/sevenfold.py | 1-442 | 442 |
| src/events.py | 1-326 | 326 |
| src/halo.py | 1-220 | 220 |
| src/module_index.py | 1-193 | 193 |

Known-and-already-filed items (per the batch brief) were re-verified against source but are
**not** re-reported below: cascade_bridge's "no reachable model" condition (order 9fb8a6b10c1f,
owner-account issue), the `NON_ENERGETIC_AXES = A.NON_ENERGETIC_AXES` line owed at
anchors.py:41-42 (confirmed still owed — `anchors.py` still carries its own literal copy of the
dict rather than the one-line alias `verify_math.py:7774` says is needed), and the two API-key
re-issues.

---

## Finding 1 — MAJOR — cascade_bridge.py:1943-1967 — an unparseable reply is the one terminal
failure this file's own ledger and bench never see

**What is wrong.** `_ask_call` classifies every OTHER way a call can fail — a deadline
(`_bury` at :1773), an account fault (`_bury(..., AUTH_BENCH)` at :1853), a throttle
(`_bury(..., _wait)` at :1879), or anything left over (`record_unrecognised(pinned.bucket, _text)`
at :1914) — and the file is explicit, repeatedly, that this three-way split is meant to be
exhaustive: the docstring at :1650-1655 states the "invariant" that `pinned` is never `None`
past that point, so every `box["failed"]` branch reaches one of the three arms above.

But a fourth terminal outcome exists and sits **outside** `box["failed"]` entirely: the stream
finishes, `box["failed"]` is `False`, and `_extract_json(_reply)` at :1943 returns `None` because
the model answered with prose, an incomplete fence, or JSON of the wrong shape. That branch
(:1944-1967) sets `served["outcome"] = "unparseable reply"` and calls
`silence.note("cascade_bridge.py:unparseable-reply")` — and returns `None`. It never calls
`_bury(pinned.bucket, ...)` and never calls `record_unrecognised(pinned.bucket, ...)`.

Consequences, both verified by reading the two functions it skips:
- **No bench.** `_alive()` only excludes a bucket via `dead_forever()`, `OWNER_EXCLUDED`, or the
  `_DEAD` dict that only `_bury` populates. A bucket that reliably answers with unparseable prose
  (e.g. a weak model that won't hold to "reply with JSON only, no prose") is claimed again on the
  very next call, forever, each time burning a full claim and up to `timeout` seconds — exactly
  the cost this file's pacing/claim/bench machinery exists to prevent for every *other* failure
  shape.
- **No ledger entry.** `record_unrecognised` is the mechanism the owner's 2026-08-25 ruling
  created specifically so "an unrecognised failure should be immediately investigated and
  resolved upon spotting it" (quoted at :1030-1041). This failure class never reaches that
  ledger, so `unrecognised_open()` / `standards` can never surface it to a person, however many
  times it recurs.
- **Ordinary production callers can't see it either.** `ask()`'s `served` parameter defaults to
  `None` for every caller except `selftest()`, `prove()` and `try_disabled()` (confirmed by
  reading `pipeline.ask_pool_first`, pipeline.py:495-496, which calls `CB.ask(system, prompt,
  schema)` with no `served=`). So on the ordinary path this failure is not even visible as
  "unparseable" to the caller — it is indistinguishable from any other `None`.

**How verified.** Read `_ask_call` end to end (cascade_bridge.py:1461-1970) and grepped the whole
file for `_bury(` and `record_unrecognised` call sites — they occur only at :1773, :1853, :1879
and :1914, none of which is reachable from the `got is None` branch at :1944. Cross-checked the
one caller of `CB.ask` with `served=` unset (pipeline.py:487-512) to confirm the gap is live on
the production path, not just in test tooling.

**Proposed remedy.** Treat "answered, but not parseable JSON" as a fourth named terminal
outcome with the same two obligations the other three already discharge: a short bench (this is
model-quality noise, not account or rate-limit noise — a `_bury(pinned.bucket, FIRST_BENCH)`-scale
timed bench seems proportionate, not `AUTH_BENCH`) and a `record_unrecognised(pinned.bucket,
"unparseable reply: " + _reply[:300])` call so the ledger the rest of this file trusts actually
sees it.

---

## Finding 2 — MINOR — stale `file.py:NNN` citations in corpus_db.py and backfill.py (Hard Rule
-style citation drift this project's own `identity.py` already had to correct once)

Three citations, all verified against the live files they point into:

1. **corpus_db.py:139-140** — "The project states this rule in `silence.write_json`'s docstring
   (silence.py:358-361) and restates it in `module_index.py:88-90`". `silence.py:358-361` is
   inside `silence.main()`'s `--instrument` argparse handling, not `write_json`'s docstring.
   `write_json`'s actual docstring (including the "THE TMP NAME CARRIES PID AND THREAD"
   paragraph the comment is citing) starts at silence.py:774 and the cited paragraph itself is
   at silence.py:785. `module_index.py:88-90` is likewise inside `module_index.main()`'s
   argparse `description=` string, not the "tmp name carries pid and thread" comment, which is
   actually at module_index.py:153.
2. **corpus_db.py:862** — the same claim, same drift: "silence.write_json, silence.py:358-364"
   — same wrong range as above (real location silence.py:774-830ish, paragraph at :785).
3. **backfill.py:191** — "scout.py's own analogous lookup (scout.py:793-795) already defaults
   to None and degrades gracefully". scout.py:793-795 is inside `scout.py`'s cycle-archiving
   error-reporting code (`sys.stderr.write("scout: %d cycle(s) could not be archived...")`), not
   a lookup at all. The actual `next((...), None)`-shaped lookup the comment is describing is at
   scout.py:811 (`rec = next((r for r in WI.load_records() if r["source"] == a.source), None)`).

**How verified.** For each citation, opened the target file at the cited range with `sed -n`,
confirmed the content did not match what the citing comment describes, then grepped the target
file for the actual described content and confirmed its real line number.

**Why this matters here specifically.** `identity.py` (one of this same batch's modules) already
had to retract exactly this failure mode once — its own comment at identity.py:591-595 records
that a `chain.py:381` citation drifted onto an unrelated line and was replaced with a
citation-by-symbol, with the explicit lesson "a line number is a citation with an expiry date
nobody can see; a function name moves with the function." These three sites in corpus_db.py and
backfill.py are the same defect, not yet given the same fix.

**Proposed remedy.** Same fix identity.py already applied to itself: cite by symbol
(`silence.write_json`'s docstring, `module_index._modules`'s comment, `scout.py`'s per-source
`next(..., None)` lookup) rather than by line number, or re-point the line numbers and accept
they will need re-verifying again later.

---

## Finding 3 — QUESTION / low-impact — identity.py:474-477 and :707-710 test `inv.get(k)` for
truthiness, not `k in inv`, when resolving a host's designator-inventory key

`mine()`'s own docstring (identity.py:189-196) is explicit that a mined host with **no**
designators is deliberately given an empty-dict entry (`{}`) rather than no key at all, and that
this distinction matters — `stale_hosts()` relies on key presence, not truthiness, to tell
"mined, found nothing" apart from "never mined".

`continuities()` (identity.py:470-479) and the equivalent hand-rolled loop in `main()`
(identity.py:706-710) both walk `_inv_keys(host)` (the three candidate spellings a host's key
might be stored under) and pick the first one where `inv.get(k)` is *truthy*:

```python
for k in _inv_keys(host):
    if inv.get(k):
        counts = inv[k]
        break
```

Because an empty dict is falsy, a host whose **canonical** key legitimately resolves to `{}`
(mined, no continuities found — a real, valid answer per `mine()`'s own docstring) is not
accepted here; the loop instead falls through to the next candidate spelling. In the overwhelming
majority of cases this is harmless — the fallback spellings won't exist as keys either, so
`counts` ends up `{}` regardless, the same answer that was already correct. The only way this
produces a *wrong* answer is if a fallback spelling (the raw host string, or the
dot/hyphen-to-underscore hand-fold) happens to also exist in `inv` as a **different** host's real
key — i.e. a spelling collision across two distinct hosts — in which case `continuities()` would
silently report a different host's continuity designators.

I could not find a live instance of such a collision by inspection of the three-key derivation
in `_inv_keys` (identity.py:437-460), and `cachekey.host_dir()`'s whole stated purpose is
collision-free naming, so I am filing this as a question rather than a finding: is the truthy
check (`if inv.get(k):`) intentional here (treat empty-dict-for-this-host the same as
key-absent, since the visible result is the same either way), or should it be `if k in inv:` to
preserve the "empty dict is itself a real answer" distinction `mine()`'s docstring cares about,
for the collision case?

**How verified.** Read `mine()` (identity.py:154-200, especially the "A VISITED DIRECTORY GETS A
KEY EVEN WHEN IT HAS NO DESIGNATORS" comment at :189-196), `stale_hosts()` (:251-264), `_inv_keys`
(:437-460), `continuities()` (:470-479), and the CLI's parallel hand-rolled copy (:703-710).

---

## What I read and found nothing wrong in

- **cascade_bridge.py** — the entire classifier stack (`permanent_refusal`, `named_transient`,
  `pool_exhausted`, `client_rejection`, `local_transport`, `_size_refusal_permanent`,
  `retry_after_seconds`, `dead_forever`) was read line by line against its own extensively
  documented history of prior bugs; every documented fix was verified present in the current
  code (word-boundary regexes, the `client_rejection` companion-word gate, the size-refusal
  arithmetic guard, the graded/timed bench, the compare-and-swap in `record_unrecognised`
  including its read-back verification, the `engine()`/`thread_engine()` double-checked-locking
  publication order). The four `file.py:NNN` citations into `cascade/engine.py` (:400, :411,
  :763, and the paired `:343`) were checked against the live `C:\Users\imarl\cascade\cascade\
  engine.py` and are all exactly correct.
- **corpus_db.py** — `rebuild()`, `freshness()`, `drift()`, `_freshness_banner()`, the
  `SPINE_LOOKUP_FAILED`/`HOST_LOOKUP_FAILED` sentinel handling, and the atomic-write/landed-verdict
  discipline throughout were read in full; all match their documentation and each other.
- **identity.py** — the three-test `_is_continuity` classifier (orthography, branching,
  population), the incremental stale-cache repair in `load()`, and the epoch-probe strict/loose
  split in `epoch_of()` were read in full and are internally consistent.
- **anchors.py** — all five anchor definitions and every graded `verdict()` in `run()` were read;
  the invariants, their gating order, and the deliberately-ungraded items (with reasons stated)
  are consistent with the code that follows them.
- **backfill.py** — `roster()`'s uncapped category walk, `lead()`'s prose-detection, and
  `backfill_source()`'s ranking-by-size-with-failed-lookups-ranked-as-unknown logic were read in
  full and match their extensive inline justification.
- **sevenfold.py** — `shelve()`/`seams()`'s window-plus-median-eligibility cut selection was read
  in full against its documented history of two rejected simpler designs; the arithmetic in
  `_even_cuts` and the `TIERS`/`SOURCE_TIERS`/`WORLD_TIERS` split in `build()` are consistent.
- **events.py** — `_looks_like_a_sentence`, `_fragments`, `shelf_positions`, and `parse()`'s
  heading/age/code bookkeeping were read in full; no cap, no fuzzy matching, matches its stated
  contract with `threads.py`.
- **halo.py** — the roster and `compute()`'s per-axis provenance tagging were read in full; no
  issues found (the file itself correctly notes the same defect shape is filed separately against
  `wh40k.py`, a module outside this batch).
- **module_index.py** — `_modules()`'s recursive walk, the duplicate-group-name and
  stale-group-name checks, and the atomic write with a carried exit code were read in full and
  are correct.
