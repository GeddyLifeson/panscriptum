# Batch 05 Audit — run27

Modules read in full, every line:
- src/read.py — 1135 lines
- src/identity.py — 423 lines
- src/worldseed.py — 327 lines
- src/render.py — 252 lines
- src/profile.py — 201 lines
- src/physics.py — 149 lines

Total: 2487 lines across 6 modules.

---

## PRIORITY: read.py concurrency trace (this run's live issue)

**Question asked: how many callers can be in flight at once, what decides it, can a cloud call
ever bypass the local gate.**

### The mechanism (CONFIRMED, fully traced)

- `GATE_CLOUD_N = 16` (read.py:274, constant).
- `GATE_LOCAL_N = max(1, int(env PANSCRIPTUM_GPU_SLOTS or OLLAMA_NUM_PARALLEL or "2"))`
  (read.py:283-284). **Checked this machine's actual shell: `OLLAMA_NUM_PARALLEL=2`,
  `PANSCRIPTUM_GPU_SLOTS` unset → GATE_LOCAL_N=2 in practice, not just in theory.**
- `_gate()` (read.py:291-300) returns `_GATE_CLOUD` (16 permits) only when
  `tuning.regime() == "cloud"` exactly; every other regime string (`"local"`, `"starved"`, and
  any future value — confirmed by reading tuning.py:188-210, `regime()` only ever returns one of
  those three strings) falls through to `_GATE_LOCAL` (2 permits by default on this machine).
- `_ask()` (read.py:328-337): when the chosen gate is `_GATE_LOCAL`, the **entire**
  `_ask_ungated()` call is run inside `_card_gate()` — not just the eventual GPU call. That
  ungated function (read.py:340-421) is the full ladder: up to 2 quick Cascade (cloud pool)
  attempts, then possibly one local GPU attempt, then up to 5 more Cascade attempts with a
  backoff ladder (`BACKOFF = (2, 5, 12, 30)`, summing to ~49s of sleep across the ladder, before
  even counting network/model latency per attempt), then a final local GPU attempt.
- So: **whenever `tuning.regime()` reads anything other than `"cloud"`, only GATE_LOCAL_N (2 by
  default here) requests can be in flight system-wide, no matter how many worker threads exist
  or how many cloud buckets are actually free.** A cloud-bound call does NOT bypass the local
  gate in this state — the docstring's own claim that "on cloud the wide gate never binds" is
  true, but the mirror claim doesn't hold: when regime reads local/starved, a call that is
  entirely bound for Cascade (never touches the GPU) still consumes one of only 2 global permits
  for its whole round trip, including all its cloud retries and backoff sleeps.

### The arithmetic that matches the reported numbers

`GATE_CLOUD_N / GATE_LOCAL_N = 16 / 2 = 8`. The reported cloud-capable floor is ~900 calls/hour;
`900 / 8 = 112.5`, which is within rounding of the reported measured **112 calls/hour**. This is
a striking match and is consistent with: whatever throughput the system could sustain at
`GATE_CLOUD_N` concurrency, it is instead getting `GATE_LOCAL_N` concurrency because the regime
label has fallen out of `"cloud"` — even though (per the brief) 29 buckets have real headroom.

### Why this can self-reinforce (SUSPECTED — tuning.py not in this batch, noted for the record)

Read tuning.py:188-210 for context only (not one of this batch's modules, not audited line by
line). `regime()` downgrades away from `"cloud"` when the recently measured Cascade success
rate drops below `CLOUD_MIN_SUCCESS`, once enough calls have been judged. If the narrow local
gate is itself causing calls to queue/time out/retry slowly, that could depress the measured
"recent success rate" independent of whether the 29 buckets actually have capacity, which would
keep `regime()` reading `"local"/"starved"` and keep the gate narrow — a plausible feedback
loop. Flagging as a hypothesis for the supervisor to check against tuning.py's actual
`cloud_success_rate()` definition, not a confirmed second bug.

### Verdict

CONFIRMED, HIGH severity, matches the known-open note exactly, with a concrete mechanism and
matching arithmetic: `_gate()` (read.py:291-300) + `_ask()` (read.py:328-337) route the FULL
cascade-then-maybe-local ladder — cloud attempts included — through the narrow `GATE_LOCAL_N`
semaphore whenever regime is not literally `"cloud"`, collapsing system-wide concurrency to 2
in-flight requests regardless of true cloud-bucket headroom.

---

## read.py — additional findings

### read.py:605-760 `read_entity` cap_chunks truncation (KNOWN-OPEN, reconfirmed)

CONFIRMED, HIGH. `chunks = chunks[:cap_chunks]` (line 667) happens before `skipped` is computed
(line 668) and before the per-chunk ask loop (line 685+) that populates `unanswered`. Chunks
excluded by the cap never enter the loop, so they can never contribute to `unanswered`, so
`if unanswered: return out` (line 753) never fires purely because of the cap, and the entity is
written to the permanent per-entity cache (line 755-759) as complete — even though its own pages
were only partially read. Only triggers when `--chunks` is passed (default `None`, uncapped), so
day-to-day full runs are unaffected, but any capped/pilot run poisons the cache permanently for
every entity it touches.

New observation around it: `skipped = sum(len(b) for b in text.values()) // size - len(chunks)`
(line 668) is computed using `len(chunks)` **after** the cap slice, so the reported
`chunks_skipped` field conflates two different reasons for exclusion — chunks dropped by the
mention/action-verb filters, and chunks dropped by `cap_chunks` — into one number. A caller
reading the output record cannot tell how much of "skipped" was the cap's doing. Low severity on
its own, but it also means the cap's true impact is invisible in the very record that documents
it.

### read.py:264-337 worker/gate throttle (KNOWN-OPEN, reconfirmed — see PRIORITY section above)

Already covered in full above.

### CASCADE_TRIES comment mismatch (NEW, CONFIRMED — lens 6)

read.py:211-213:
```
# Attempts through the pool before a chunk is handed to the local GPU. Each attempt claims a
# different bucket, so three is three providers, not one provider three times.
CASCADE_TRIES = 5
```
The comment's illustrative number ("three is three providers") does not match the actual
constant (`5`). Also, "before a chunk is handed to the local GPU" is stale relative to the
current flow: `_ask_ungated` (read.py:374-421) now tries a local GPU call *before* the
`CASCADE_TRIES`-attempt backoff ladder runs (the "two quick attempts then GPU, only if both
decline does backoff start" logic), so CASCADE_TRIES attempts happen both after an earlier local
attempt and, if all fail, before one final local attempt at line 421. Low-medium severity —
doesn't change behaviour, but it's a comment giving a wrong number and a stale description of
control flow right next to the constant it's supposedly explaining.

### Minor unlocked counters (NEW, SUSPECTED, LOW)

`_FELL_BACK[0] += 1` (read.py:385, 402) and `_GPU_DOWN_UNTIL[0] = time.time() + GPU_BENCH`
(read.py:515) are mutated from multiple worker threads with no lock, unlike `done{}`/`_rate_log`
in `run()` which are explicitly protected by `lock` (read.py:975, 984). Under the GIL a single
`+=` on a list element is not guaranteed atomic across a thread switch; worst case is an
undercounted `_FELL_BACK` diagnostic. This is a reporting-only counter, not data-path state, so
impact is limited to progress-line accuracy (read.py:1029) rather than correctness of what gets
cached — flagging because lens 5 asks for read-modify-write without a lock, and the rest of this
file is otherwise careful about exactly this.

---

## identity.py — findings

### `_is_continuity` branching test rejects the module's own worked example (NEW, CONFIRMED, HIGH — lens 1 + lens 6)

identity.py:57-60 (module docstring):
> "Either alone admits it. `(Revelation)` shares no bearers yet and is obviously a continuity,
> while `(Fates)` has one bearer and is obviously a continuity because that bearer exists in
> three other branches."

identity.py:180-207 (`_is_continuity`), specifically:
```python
n = stat["bearers"] if isinstance(stat, dict) else stat
shared = stat.get("shared", 0) if isinstance(stat, dict) else 0
if n >= MIN_BEARERS:
    return True
return n >= 2 and shared >= max(2, 0.5 * n)
```
The branching test requires `n >= 2` before it can ever return True. A designator with exactly
one bearer (`n == 1`) — precisely the `(Fates)` example the docstring cites as the canonical
case the branching test exists to catch — short-circuits to `False` on `n >= 2` alone, no matter
how large `shared` is (and `shared` is bounded by `n`, so it can be at most 1 anyway). The
docstring's claim that a single-bearer designator "is obviously a continuity because that bearer
exists in three other branches" is not something the code can currently produce: `MIN_BEARERS`
(population test) needs 3, and the branching test needs `n >= 2`. A single-bearer designator can
never be recognised as a continuity by this function, contradicting its own documented design.

**Failure scenario**: a franchise where a new alternate continuity has exactly one character
written up on the wiki so far (the docstring's own stated common case — "a small wiki's
alternate timeline may only have a handful of characters written up", identity.py:96-98, is
explicitly why `MIN_BEARERS` was set as low as 3, yet 1-bearer designators still fall through
entirely). `identify()` (identity.py:237-248) then returns `continuity=None` for that title
because `desig not in continuities(host, inv)`, so `node()` (identity.py:251-263) builds the
SAME graph node for the alternate-continuity character as for the base-continuity character of
the same name — silently merging two distinct beings into one comparison-graph identity. This is
exactly the "wrong merge is not recoverable" failure the module's own docstring (identity.py:96-98)
says is the worse of the two possible errors, arrived at by the very code meant to prevent it.

### Duplicated, non-parity host-name sanitisation (NEW, SUSPECTED, LOW — lens 6, "parity that is not actually parity")

`mine()` (identity.py:147-177) keys its inventory by the raw directory names already present
under `data/feats/` — which were sanitised by whatever wrote that cache (elsewhere in the
project, e.g. read.py's own `cache_path()` uses `re.sub(r"[^A-Za-z0-9]+", "_", host)[:40]`).
`continuities()` (identity.py:226-232) instead re-derives a key from a caller-supplied host
string with `host.replace(".", "_").replace("-", "_")` — a different sanitiser with no
truncation and no handling of any character besides `.` and `-`. For ordinary short fandom
domains (all dots, under 40 chars) these two produce the same string, so I could not find a
live mismatch, but the two implementations are not parity by construction: a host longer than
40 characters, or containing any punctuation other than `.`/`-`, would silently fail to look up
the correct inventory entry and `continuities()` would fall back to `{}` at line 230
(`inv.get(key) or inv.get(host) or {}`), which reports zero continuities for that host without
any error. Flagging as a fragility rather than a proven live bug.

---

## worldseed.py — findings

### Raw `open(...,'w')` + `json.dump` on a shared data file — two-writer contract violation (NEW, CONFIRMED, HIGH — lens 4)

worldseed.py:317-322:
```python
if args.write:
    path = os.path.join(HERE, "data", "WORLDSEEDS.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({w["designation"]: {"address": address(w), **w} for w in worlds},
                  f, indent=2, ensure_ascii=False)
    print(f"\nwrote {path}")
```
This writes `data/WORLDSEEDS.json` directly, with no temp file and no `silence.replace_retry` /
`silence.write_json`, unlike every other JSON write in this batch's modules (compare
read.py:756-759, read.py:598-600, read.py:876-879, identity.py:219-222, all of which stage to a
`.tmp` and call `silence.replace_retry`). A crash, kill, or Ctrl-C mid-write leaves a truncated
or empty `WORLDSEEDS.json` in place — the file this module's own docstring (worldseed.py:36-37)
calls "the whole library" of world addresses, "against gigabytes of saved maps". Any reader of
that file (in-process or a later run) that opens it while this write is in flight, or after an
interrupted write, gets corrupt JSON with no self-healing path (unlike read.py's readfeats cache,
which explicitly deletes-and-re-earns a corrupt file — read.py:608-621). Confirmed by direct
code read; this is the `--write` CLI path in `main()`, so it fires whenever this tool is run
with that flag, not a rare corner case.

### `build_all(limit=...)` cap (NEW, LOW, design question)

worldseed.py:282-283: `if limit and len(out) >= limit: return out` inside the entries loop. This
is an explicit truncation gated behind an opt-in `--limit` CLI flag (default `None`, uncapped —
mirrors read.py's own `--limit`/`--chunks` pattern). Given Hard Rule 0's absolute wording ("No
limit, no cap, no sample... EVER"), flagging for the supervisor's judgment rather than as a firm
bug: unlike read.py's `--chunks`, nothing here writes a permanent "complete" record under the cap
(this function just returns a shorter Python list for the caller to print/write), so the
"wearing the same shape as the real one" danger described in CLAUDE.md is smaller — but the flag
exists and nothing marks its output as partial if someone pipes it into something else. Worth a
policy call, not treating as a confirmed defect.

---

## render.py — findings

No correctness bugs, swallowed failures, cap violations, two-writer violations, or concurrency
issues found on a full read. Notes, none rising to a finding:
- `main()`'s `--write` path (render.py:239-247) writes per-tier SVGs via a plain `open(p,'w')`,
  but these are rendered deliverables (`output/views/{tier}.svg`), not shared coordination state,
  so the two-writer contract's "shared state/JSON files" framing does not obviously apply — noting
  this only so the supervisor can confirm that reading is correct rather than silently agreeing.
- `nm = str(ch.get("name", ""))[:26]` (render.py:140) truncates a display label for the SVG; the
  untruncated `ch["id"]` is still rendered per-node, so this is a cosmetic label-width limit, not
  a data-dropping cap.

## physics.py — findings

No correctness bugs, swallowed failures, cap violations, two-writer violations, or concurrency
issues found on a full read. `kinetic()` correctly switches Newtonian/relativistic at the stated
threshold with no discontinuity of consequence at the boundary; `joules_for()` and `_b32`-style
lookups all raise rather than silently defaulting, consistent with the module's stated design
philosophy. This module is a template for how `profile.py`'s `encode()` (see below) arguably
should have handled its own out-of-range input.

---

## profile.py — findings

### `decode()`'s validating regex is looser than the alphabet it actually decodes (NEW, CONFIRMED, MEDIUM — lens 1)

profile.py:94-98:
```python
def decode(profile):
    m = re.fullmatch(r"PS-([0-9a-z]+)-([a-z]{2})([a-z])-([0-9a-z]{4})-([0-9au])([0-4])", profile)
    if not m:
        raise ValueError(f"not a world profile: {profile!r}")
    addr, gr, rg, feats, band, att = m.groups()
    address = _unb32(addr)
    ...
```
`B32 = "0123456789abcdefghjkmnpqrstuvwxyz"` (profile.py:52) deliberately excludes `i`, `l`, `o`,
`u` (Crockford-style), but the regex groups for the address (`[0-9a-z]+`) and the four feature
characters (`[0-9a-z]{4}`) accept the full lowercase alphabet, `i`/`l`/`o`/`u` included. A
profile string that is syntactically well-formed by the regex but contains one of those four
letters in the address or feature positions passes validation, then crashes inside `_unb32()`
(profile.py:79-83, `B32.index(ch)`) or the features comprehension (profile.py:100,
`tbl[B32.index(ch)][0]`) with an unhandled `ValueError: substring not found` — not the clean
`"not a world profile"` message the function's own guard clause exists to produce. Because
`encode()` (profile.py:86-91) only ever emits valid B32 characters, this cannot happen on a
round trip of the module's own output; it can only be hit by hand-typed, corrupted, or
externally-supplied profile strings — which is exactly the situation the regex guard appears to
be there for.

### `encode()`'s band lookup has no defensive handling, unlike the same field in worldseed.py (NEW, CONFIRMED mechanism / SUSPECTED real-world trigger, MEDIUM-HIGH — lens 1 + lens 6 parity)

profile.py:90: `b = "u" if band in (None, "unassayed") else B32[BANDS.index(band)]`.
`BANDS = ["M0", ..., "M10"]` (profile.py:66) requires an **exact** string match (case-sensitive,
no whitespace). `band` is threaded through from `w.get("band", "unassayed")` in `build_all()`
(profile.py:150), where `w` comes from `worldseed.build_all()`, whose `band` field is `e.get(
"magnitude") or "unassayed"` (worldseed.py:281) — i.e. whatever the catalogue's `magnitude`
field literally contains, unmodified. Compare worldseed.py's own handling of the same value
(worldseed.py:167): `tier = 0 if band in ("unassayed", None) else max(0, int(re.sub(r"\D", "",
band) or 0))` — deliberately tolerant of any string shape, extracting digits rather than
requiring an exact match. `profile.py`'s `encode()` has no equivalent tolerance: any magnitude
string that is not exactly one of `"M0"`..`"M10"` or exactly the lowercase literal `"unassayed"`
(e.g. a stray `"Unassayed"` with different casing, `"M4.31"` in decimal-Assay notation, `"TBD"`,
or any other non-canonical label that might exist in `data/`) raises an unhandled `ValueError`
from `BANDS.index(band)`.

**Failure scenario**: `build_all()`'s loop (profile.py:141-152) has no per-entry try/except, so
one catalogue entry with a non-canonical `magnitude` string aborts the entire function — every
world after the bad one in iteration order is silently never profiled, and the caller (e.g.
`main()`) gets a crash instead of a partial or complete result. This is the opposite of read.py's
posture in this same batch, where per-entity work is wrapped in try/except specifically so one
bad record can't take down a whole run (read.py:978-983). I could not confirm from this batch's
files alone whether `data/`'s actual `magnitude` values are always clean `"M0"`-`"M10"` strings
(that data and the code that writes it live outside this batch), so the triggering condition is
SUSPECTED rather than proven — but the code-level gap and its blast radius (whole-run crash, no
partial output) are CONFIRMED by direct read.

---

## Summary of confirmed vs suspected

CONFIRMED (traced or matches known-open evidence): read.py gate-forces-cloud-through-local-gate
(priority item), read.py cap_chunks/unanswered interaction, identity.py `_is_continuity`
single-bearer branching gap, worldseed.py raw write of WORLDSEEDS.json, profile.py regex/alphabet
mismatch in `decode()`, profile.py band-lookup crash mechanism in `encode()`.

SUSPECTED (plausible, not independently provable from this batch alone): tuning.py feedback-loop
hypothesis around regime() and the gate, identity.py host-sanitiser parity gap, profile.py's
real-world trigger rate for non-canonical magnitude strings.
