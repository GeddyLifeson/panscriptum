# AUDIT — BATCH 05 (run26)

Modules read in full, line by line: `src/read.py` (1135 lines), `src/identity.py` (423),
`src/worldseed.py` (327), `src/genre.py` (247), `src/profile.py` (201), `src/catalog.py` (127).
Total 2,460 lines. Also read for context (not part of this batch, not exhaustively audited):
`src/pipeline.py` (write_record / write_record_catalogue / _landed), `src/silence.py`
(replace_retry / note / write_json), `src/tuning.py` (regime / workers / profile),
`src/overnight.py` (how read.py is actually launched in production).

Special-focus items from the brief are addressed inline and flagged **[FOCUS]**.

---

## MAJOR

### M1 — `--chunks`/`cap_chunks` bypasses the "cached-if-fully-read" write guard [FOCUS]
`src/read.py:605-760` (`read_entity`).

The file has an extensively-documented guard: an entity's readfeats cache is only written when
`unanswered == 0` (lines 742-759, "AN ENTITY IS CACHED ONLY WHEN IT WAS ACTUALLY READ, ALL OF
IT... read_entity returns the cache forever and the queue never revisits"). That guard is sound
for its stated case (a chunk that was offered to a transport and got no answer).

It does **not** cover a second way an entity can be cached with fewer than its full chunk set:
`cap_chunks` truncates the candidate list *before any chunk is ever offered to a transport*
(lines 666-667):

```python
chunks = [(t, c) for _, _, t, c in chunks]
if cap_chunks:
    chunks = chunks[:cap_chunks]          # <-- happens BEFORE the ask loop
skipped = sum(len(b) for b in text.values()) // size - len(chunks)
```

Chunks removed here are never counted in `unanswered` (that counter only increments inside the
ask loop, line 705, for chunks that *were* offered and declined). They land in
`chunks_skipped` instead (line 737), which the write guard at line 753 does not look at:

```python
if unanswered:
    return out
... write cache ...
```

So `--chunks N` (or `--one HOST ENTITY --chunks N`, both wired straight through from `main()`,
lines 1107-1116) writes a **permanent** "complete" cache for any entity whose real chunk count
exceeds N, using only its top-N-by-density chunks. Per the file's own logic, a later full
`--run` with no cap hits the top-of-function short-circuit (`if os.path.exists(path): return
json.load(...)`, lines 608-614) and returns that capped record forever — the exact
"permanently incomplete, indistinguishable from an entity with genuinely fewer feats" failure
the big guard comment describes, arriving through the one door the guard doesn't watch.

**Live exposure today:** the production supervisor (`overnight.py:704-706`) launches
`read.py --run --workers N` with no `--chunks` flag, so the automated loop does not currently
trigger this. It is a live trap for exactly the workflow `CLAUDE.md` tells operators to use
("Pilot before you scale" — rule 6): a `--chunks 12` pilot run followed by a full run does not
self-heal; the piloted entities stay capped until someone manually deletes their cache files.
Given this module's history (this exact "permanently incomplete, cached forever" failure has
already been fixed once for the `unanswered` case, 2026-08-24 per the docstring), the guard
should check `len(chunks) < total_available_chunks_for_this_entity` (or equivalently, refuse to
write whenever `cap_chunks` actually reduced the candidate set) the same way it already refuses
to write when `unanswered`.

### M2 — Regime misjudgment collapses concurrency for cascade calls too, not just local ones [FOCUS]
`src/read.py:264-337` (`_gate`, `_card_gate`, `_ask`) and `src/read.py:1083-1092` (`run`'s
worker cap), combined with `src/tuning.py:188-244` (`regime`, `workers`).

This is the most plausible in-scope explanation for the reported symptom ("32 calls/hour
against a floor of 900, one bucket doing all 8 calls in 15 minutes despite 27 buckets having
headroom"):

1. `run()` requests a worker count, then clamps it through `T.workers()` (read.py:1086):
   `capped = T.workers(int(workers))`. `tuning.workers()` returns `min(requested,
   PROFILES[regime]["workers"])`, and `PROFILES` caps `"local"` at 2 workers and `"starved"` at
   1 (`tuning.py:98-101`). So if `tuning.regime()` reads "local" or "starved", **the whole run
   is capped to 1-2 concurrent callers**, regardless of how many remote buckets have quota.

2. Independently, `_ask()` (read.py:328-337) picks its concurrency gate purely from the same
   regime label via `_gate()` (line 291-300): when the regime is not `"cloud"`,
   `_gate()` returns `_GATE_LOCAL` (2 permits), and `_ask()` then wraps the **entire**
   `_ask_ungated` ladder — including the two "quick" cascade attempts and the whole
   `CASCADE_TRIES`-attempt backoff ladder against the cloud pool — inside `_card_gate()`. That
   gate is sized for the local GPU's slot count (`GATE_LOCAL_N`, default 2), not for how many
   cloud buckets are healthy. A call that never touches the GPU is still throttled as if it
   did, purely because of how the regime label reads.

`tuning.regime()` (tuning.py:188-212) reads "local"/"starved" whenever either fewer than
`CLOUD_MIN_BUCKETS` (3) buckets *answer a proof call*, or — separately — the **measured success
rate over the last 15 minutes** (`cloud_success_rate`, tuning.py:160-186, backed by
`state/cascade_scratch.db`) is below `CLOUD_MIN_SUCCESS` (0.35), once at least
`MIN_CALLS_TO_JUDGE` (20) calls have been recorded. "27 buckets have headroom" (quota) is not
the input to this decision; recent *success rate* is. If most attempts in the last 15 minutes
were erroring for any reason other than quota (rate limit shape, transient outage, a
misbehaving bucket), `regime()` will read "local"/"starved" even with real capacity sitting
idle elsewhere, and both throttles above then collapse the whole reader to 1-2 concurrent
callers. With only one caller in flight, cascade's own bucket-selection (owned by
`cascade_bridge.py`, not in this batch) never gets pushed past whichever bucket answers first —
which would fully explain "one bucket did all 8 calls" as a consequence of read.py's own
concurrency having been squeezed to ~1, not a routing bug in isolation.

This is a *design coupling*, not a one-line typo: read.py trusts `tuning.regime()`'s label
completely and has no cross-check against the thing the brief's own symptom describes (headroom
existing that the label doesn't reflect). Recommend either (a) having `_gate()`/`run()`'s
worker cap key off something closer to "answering buckets right now" rather than the blended
15-minute success-rate signal for the *cascade-bound* portion of the ladder, since that portion
never touches the GPU and gains nothing from being throttled to GATE_LOCAL_N, or (b) at minimum
logging what `tuning.regime()`'s `why` string said at the moment throughput craters, so this
symptom is diagnosable without re-deriving the mechanism from source. **`tuning.py` itself is
out of this batch's scope** — flagging the read.py-side effect and the exact mechanism for
whoever owns tuning.py / cascade_bridge.py next.

### M3 — "Chunk counter going backwards" is not explained by anything read.py persists; likely a process-restart artifact downstream [FOCUS]
`src/read.py:974-975` (`done = {...}`), `src/read.py:1043-1045` (`CHUNK_BUDGET`).

Nothing in read.py itself is a plausible source of a monotonic total *falling* within one
process: `CHUNK_BUDGET` is computed once per `run()` invocation as `sum(chars for r in todo) //
size` (line 1045) — a denominator over the corpus `queue()` returns, which only grows as more
evidence accumulates, and `done["chunks"]` only ever increments (line 990, under `lock`) for
the life of that process. There is no re-glob, resample, or recompute of either value mid-run.

What *is* true: `done` is a plain in-process dict, seeded to zero at the top of every `run()`
call (line 974), with **no persistence** anywhere (no state file records a running total across
process restarts). Anything downstream — a supervisor or `dashboard.py` (not in this batch) —
that displays or re-derives a "chunks done" total by reading read.py's own printed progress line
or by re-summing something tied to this process's lifetime, rather than a total independently
aggregated from the on-disk readfeats cache, would see that number reset toward zero every time
`read.py --run` is relaunched (e.g. by `overnight.py`'s per-cycle supervision, or after a kill
per `foreman.py`'s stall-detection). A `-3689` drop over 31 minutes is consistent with a restart
losing an in-memory total of that rough size, not with anything read.py writes to disk being
wrong.

Two secondary candidates inside read.py that could shift an *aggregate-from-disk* total by a
smaller, noisier amount (not a clean 3689): the self-healing corrupt-cache delete at
lines 608-621 (`os.remove(path)` then re-earned from scratch — a brief window where that
entity's cache is absent from disk, undercounting anyone re-scanning `data/readfeats/` live),
and the entity-keyed vs. old-keyed chunk-cache migration documented at lines 542-570 (old-keyed
entries are "left in place, not deleted" — harmless for read.py's own counters, but a stale
external index built by scanning `data/chunkfeats/` before vs. after that migration would see
different totals for the same corpus). Neither is the batch's file to fix, but both are
mechanisms worth ruling in or out before concluding it's read.py's fault: **recommend checking
dashboard.py's aggregation source next** (whether it sums from the readfeats cache on disk, or
from a live progress feed keyed to this process's lifetime).

---

## MINOR

- **`read.py:909-964` (`queue`)** — several `continue`s drop an entity from the queue with zero
  accounting: no host resolved (`hosts.get(r["source"])` miss, line 911), evidence cache file
  absent (line 918), or empty `ev.get("text")` (line 947, silently marked `skip: True` in the
  qcache with no counter). Contrast with the same file's own discipline elsewhere (`thin`,
  `skipped`, `chunks_skipped` are all counted and printed) — these three exclusions have no
  comment claiming they're legitimate and no visible count of how many entities they remove.
  Given Hard Rule 0's exact concern ("a cap does not fail, it returns a smaller universe wearing
  the same shape as the real one"), recommend logging `n` for each skip reason in `run()`'s
  startup banner.
- **`read.py:381` and `read.py:397`** — both exception handlers in `_ask_ungated` (the "quick"
  cascade attempts and the backoff-ladder cascade attempts, two different failure sites) call
  `silence.note("read.py:188")` with the *same* literal site id, apparently left over from
  before the ladder was split into two loops. Any diagnostics that discriminate by site id
  (the whole point of `note()`, per `silence.py`'s own docstring) can't tell "the quick probe
  failed" from "the full backoff ladder exhausted every bucket" from this signal alone.
- **`read.py:1114-1119` (`--one` CLI path)** — calls `read_entity(config(), ...)` directly
  without first calling `ensure_transport()`. `read_entity` computes `size = CLOUD_CHUNK if
  _CASCADE_OK else CHUNK` at line 639 before any `_ask()` call would lazily resolve
  `_CASCADE_OK`, so for this path `_CASCADE_OK` is still `None` and `size` silently falls to the
  `CHUNK`-not-`CLOUD_CHUNK` branch regardless of the real transport. Currently harmless only
  because `CLOUD_CHUNK = CHUNK` (line 93) — the file's own history (lines 74-93) shows this
  constant has been deliberately different before and could be again, at which point `--one`
  debugging would silently chunk at the wrong size.
- **`read.py:651-667`** — the "RANKED AND CAPPED" comment block (651-660, arguing a default
  12-chunk cap is correct depth-bounding) is stale: no code anywhere sets a default `cap_chunks`
  (the signature default is `None`, the CLI default is `None`). The very next comment (662-664,
  "Not truncated: a cap here decides on the entity's behalf...") documents the actual current
  behaviour. Currently harmless since the code is right, but the surviving comment block
  contradicts it and could lead a future maintainer to believe a cap is baked in by default when
  it isn't.
- **`read.py:210, 220, 385/402`** (`_FELL_BACK`, `_GPU_DOWN_UNTIL`) and **`read.py:288-300`**
  (`_GATE_STATE`) — module-level mutable state (plain lists/dicts, not `threading.Lock`-guarded)
  read-modified-written from multiple worker threads. `_FELL_BACK[0] += 1` in particular is a
  non-atomic increment that can lose counts under a race. All are diagnostic-only counters (not
  used for correctness gating), so severity is low, but they're exactly the "shared mutable
  module state without a lock" pattern the audit is asked to flag.
- **`identity.py:229`** (`continuities`) — hand-rolls host-name sanitization as
  `host.replace(".", "_").replace("-", "_")` instead of reusing the canonical
  `re.sub(r"[^A-Za-z0-9]+", "_", host)` sanitizer that `feats.py`/`read.py` use to build the
  `data/feats/<host>` directory names `mine()` (identity.py:158-177) keys its inventory by. The
  two only agree when the host string has no *runs* of consecutive non-alnum characters and no
  non-alnum characters other than `.`/`-`. For a host where they diverge, `inv.get(key) or
  inv.get(host) or {}` (line 230) silently falls through to `{}` — a host with real mined
  continuities would report zero. Recommend calling the shared sanitizer instead of
  reimplementing it.
- **`worldseed.py:167`** (`to_options`) — `tier = ... int(re.sub(r"\D", "", band) or 0)` strips
  *all* non-digit characters from the magnitude band string. A compound/decimal band such as
  `"M4.5"` would parse as tier 45, not 4 (masked in practice only because `states = min(40,
  ...)` clamps the result). Per `CLAUDE.md`'s Hard Rule 3, catalogue magnitude is meant to stay
  band-only (`M4`, not `M4.31 ± 0.30`), so this is unlikely to be hit today, but the parser
  doesn't defend against it if that assumption ever slips.
- **`worldseed.py:266`** (`build_all`) — `g = gid.get(src, 0)` folds every source *absent* from
  `CONTINUITY_GROUPS.json` into "group 0" and gives it group 0's onomasticon register
  (`reg_by_group.get(g, "classical")`), rather than a genuinely source-agnostic default. Cosmetic
  (affects only the seeded naming register of a worldseed address), but conflates "unknown
  group" with "group 0" rather than treating them as distinct.
- **`profile.py:142`** (`build_all`) — `src = w["designation"].split("::")[0]` recovers the
  source key from worldseed's `f"{src}::{nm}"` designation by splitting on the first `"::"`.
  If a source's *own name* ever contained the literal substring `"::"`, this would silently
  truncate `src` and miss the genre/register lookup (falling back to
  unclassified/classical for that source only). No evidence any current source name does this;
  flagging as a fragile assumption rather than a live bug.

---

## QUESTIONS / follow-ups for other batches

- **cascade_bridge.py** (not in this batch): given M2 above, worth checking directly whether
  `CB.ask()`'s bucket selection is randomized/round-robin or priority-ordered — if
  priority-ordered, a single healthy top-priority bucket serving every call under low
  concurrency (M2) is expected behaviour there, not a bug in that file either; it would just
  mean read.py's throttling is the actual lever to pull.
- **dashboard.py** (not in this batch): where does the "chunk counter" the owner is watching
  actually come from — a live sum over `data/readfeats/*.json`, or something tied to a single
  read.py process's lifetime? M3 above narrows this down but can't settle it without reading
  that file.
- **tuning.py `regime()`** (read for context, not fully audited): is a 15-minute
  `cloud_success_rate` window (backed by `state/cascade_scratch.db`) the right signal to gate
  *read.py's* cascade-bound concurrency specifically, given M2's mechanism? This file already
  documents (lines 68-82) that it was written specifically to fix the opposite failure mode
  (regime reading "cloud" while success was actually poor) — worth checking whether the current
  thresholds now overcorrect in the other direction for a reader that's mostly cloud-bound.

---

## Clean

- **`genre.py`** — no findings. The Hard Rule 0 `cap` parameter is explicitly refused
  (`classify_source`, lines 173-177) with a `SystemExit` and a detailed measured-impact
  docstring; `main()`'s catalogue write uses `silence.write_json` (atomic). Well-built file.
- **`catalog.py`** — no findings. Read-only CLI query tool; no writes, no concurrency, no caps
  beyond an explicitly-disclosed `missing[:30]` console display ("... and N more"), which is a
  legitimate UI bound, not a data truncation.
- **Two-writer contract**: neither `read.py` nor any of this batch's other five files write to
  `output/records/*.json` (the pipeline/catalogue two-writer files) at all — no violation
  possible in this batch. `read.py`'s own cache writes (readfeats, chunkfeats, qcache) are all
  single-writer-per-key (readfeats keyed by entity, chunkfeats keyed by content+entity hash with
  a per-worker temp filename, per lines 592-600) and go through `silence.replace_retry` for the
  atomic rename — correctly built.
