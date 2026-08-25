# AUDIT batch06 — sweep30

Scope: `src/read.py`, `src/gpu_lane.py`, `src/prose_gate.py`, `src/sevenfold.py`,
`src/autostart.py`, `src/catalogue_aurora.py`. Every line read top to bottom. Read-only:
no repo file edited, no generation or long job run. Supporting files (`cachekey.py`,
`silence.py`, `pipeline.py`, `feats.py`, `overnight.py`, `generate.py`, `prompts/system_style.txt`)
were read only far enough to verify claims made *by* the batch files, never audited in their
own right.

Method note on "REPRODUCED": for the concurrency and cache-collision findings I wrote small,
read-only Python snippets (listed inline) that exercise the real functions with mocked I/O, or
that build real cache paths against the actual `data/` tree and check them with
`os.path.exists`/`os.path.samefile` — no repo file was written by any of them. Nothing long-running
or generative was executed.

---

## src/read.py

### FINDING 1 — HIGH — REPRODUCED — `queue()` reads a third, unverified copy of the entity cache path, and it collides on disk right now

**Where:** `src/read.py:937-984` (`queue()`), specifically the path construction at 937-938:

```python
path = os.path.join(FF.CACHE, re.sub(r"[^A-Za-z0-9]+", "_", h)[:40],
                    re.sub(r"[^A-Za-z0-9]+", "_", e["name"])[:80] + ".json")
```

**What's wrong:** `cachekey.py` exists specifically to close the collision this line reopens.
Its own docstring: "Four modules built the per-entity cache path independently... `Two-Towns`
sanitiser... folds any two names that agree." The fix was: never trust a hit at a lossy path
without opening the file and checking `doc["entity"] == name` (`cachekey.owns`), used correctly
by `feats.evidence_for()` (feats.py:740, cites M23 by name) and by `read.read_entity()` itself
(read.py:627, 640, via `cachekey.write_path`/`cachekey.load`).

`queue()` is a **third reader of the same `data/feats/` cache** and it does not go through
`cachekey` at all — it rebuilds the lossy sanitized path inline and trusts whatever file sits
there, with no `owns()` check, no fallback to a disambiguated sibling.

**Reproduced, on the real corpus, no files modified:**

```python
import os, re
CACHE = os.path.join(os.getcwd(), 'data', 'feats')
def path_for(host, name):
    return os.path.join(CACHE, re.sub(r'[^A-Za-z0-9]+', '_', host)[:40],
                         re.sub(r'[^A-Za-z0-9]+', '_', name)[:80] + '.json')
p1 = path_for('callofduty.fandom.com', 'Tag Der Toten')
p2 = path_for('callofduty.fandom.com', 'Tag der Toten')
# p1 != p2 as strings, but:
os.path.samefile(p1, p2)   # -> True (NTFS case-fold)
```

Both entities are real, distinct catalogue rows today: `data/records/all-black-ops.json` carries
`"Tag Der Toten"`, `data/records/call-of-duty-zombies.json` carries `"Tag der Toten"`. Both hash
to the same file on this filesystem, `data/feats/callofduty_fandom_com/Tag_Der_Toten.json`
(`entity` field inside: `"Tag Der Toten"`, `chars_read: 41791`, 1 feat). When `queue()` builds a
priority row for `"Tag der Toten"`, it will open that file and hand `"Tag der Toten"`'s row the
*other* entity's `chars_read`/`axes`/`quantities` — this is exactly the corruption `cachekey.py`
was written to stop, reopened at a third call site.

**Why it matters:** `priority()`'s whole contract is "a run stopped at any point has read the
richest material available for that spend" (read.py:913-914). A collision breaks that guarantee
silently for the colliding pair — the misranked entity is read too early or too late relative to
its real evidence depth. This is *not* permanent data loss: `read_entity()` itself still verifies
identity via `cachekey.load()` when it actually mines the entity, so the feats collected are
correct. Only the queue's ordering is corrupted, which is why this is HIGH rather than a repeat
of the M23 incident, not a new one.

**Fix:** route `queue()`'s row lookup through `cachekey.natural_path`/`cachekey.load` (with an
`owns()` check) exactly like `feats.evidence_for()` and `read.read_entity()` already do.

---

### FINDING 2 — HIGH — REPRODUCED (isolated concurrency test) — confirms the "known open item": `_ask` runs the whole cascade ladder inside the narrow local-GPU gate

**Where:** `src/read.py:329-422` (`_ask`, `_ask_ungated`), gate selection at `_gate()` (292-301).

**Control-flow trace:** `_ask()` calls `_gate()`. When the regime reads local/starved, `_gate()`
returns `_GATE_LOCAL` (bound `GATE_LOCAL_N`, default 2). `_ask` then does:

```python
if gate is _GATE_LOCAL:
    with _card_gate():
        return _ask_ungated(c, system, prompt, schema)
```

`_ask_ungated` is the *entire* transport ladder: `ensure_transport()`, two quick Cascade
attempts, an early local try, then up to `CASCADE_TRIES` (5) more Cascade attempts with a
`BACKOFF` ladder (2/5/12/30s), and only then the final local call. All of that — including every
Cascade network attempt, none of which touch the GPU — runs while holding one of only
`GATE_LOCAL_N` permits.

**Reproduced** with a script that monkeypatches `cascade_bridge.ask`/`read._local` to short,
harmless sleeps, forces `_GATE_STATE["regime"] = "local"`, and counts concurrent threads inside
`_ask_ungated` across 8 worker threads calling `_ask()`:

```
workers: 8  GATE_LOCAL_N: 2  max_concurrent_inside_ladder: 2  elapsed: 2.207
```

Never more than `GATE_LOCAL_N` (2) of the 8 workers are ever inside the ladder at once — matching
the audit brief's "capping throughput at floor*2/16" claim exactly.

**Why it matters:** the gate's own docstring says its job is to bound *card* concurrency; here it
also bounds calls that never reach the card. Whenever `tuning.regime()` reads local/starved (which
per `_local`'s own docstring can happen even while cloud buckets ARE answering — "regime read
'cloud', so every worker passed the wide gate — while live cloud success was 4.1%", i.e. the
inverse mislabelling is already a documented incident), every worker is throttled to
`GATE_LOCAL_N` concurrent *anything*, including Cascade calls that could run 16-wide.

**Fix:** only the actual `_local(...)` call needs `_card_gate()`. The Cascade attempts inside
`_ask_ungated` should acquire (or skip) `_GATE_CLOUD` independently of which gate `_ask` picked,
or the two concerns should be split into two separate `with` blocks so the narrow gate is held
only around the GPU call.

---

### FINDING 3 — MEDIUM — REPRODUCED (code comparison) — two of three writers in this file skip the pid+thread-scoped temp name the third one was fixed to use

**Where:** `src/read.py:894-902` (`_save_qcache`) and `776-780` (end of `read_entity`), versus
`596-613` (`_chunk_put`).

`_chunk_put` was explicitly hardened:

```python
tmp = "%s.%d.%d.tmp" % (p, os.getpid(), threading.get_ident())
```

with a comment explaining the exact hazard: "two workers answering the same passage at once
opened and truncated ONE file... each writing over the other mid-dump." `_save_qcache` and the
final write in `read_entity` both still use a bare temp name:

```python
tmp = QCACHE + ".tmp"                 # _save_qcache
tmp = path + ".tmp"                   # read_entity
```

**Why it matters:** `_save_qcache` is called once per `queue()` call, single-threaded within one
process, so the in-process risk is nil — the exposure is two separate `read.py --run` invocations
overlapping (a manual run alongside the supervisor's, or two supervisor cycles overlapping).
`read_entity`'s write is riskier in principle: if the same `(host, name)` pair is ever queued
twice (e.g. an entity cited under two source records sharing a host — plausible in a crossover
franchise), two worker threads could race the identical unscoped tmp file. Both are the same
class of bug this file already diagnosed and fixed once, two functions away.

**Fix:** apply `_chunk_put`'s `%s.%d.%d.tmp` pattern to both sites (or route them through
`silence.write_json`, which already does this correctly).

---

### FINDING 4 — LOW/INFO — comment contradicts the code it sits above

**Where:** `src/read.py:206-208`:

> "Direct Ollama remains as a last resort for when Cascade is unreachable, because a transport
> that fails should degrade rather than stop."

This is contradicted by the design actually implemented 130 lines later (341-422), which the code
itself argues against under the heading **"THE GPU IS CAPACITY, NOT A LAST RESORT"** (364-374):
the GPU is tried after only *two quick* Cascade attempts, well before Cascade is exhausted, and
Cascade is retried again afterward. The GPU is not reserved for "Cascade unreachable"; it is a
scheduled middle rung. Low severity — doesn't affect behavior, just misleads a reader of the
top-of-file design note against the detailed, correct reasoning lower down in the same file.

---

### FINDING 5 — LOW/INFO — confirmed dead code, self-documented, correctly grepped

**Where:** `src/read.py:535-546` (`cache_path()`).

Docstring already states "it has no callers left." Confirmed by grep across all of `src/`,
`launchers/`, and `config.yaml`: no call site anywhere calls `read.cache_path(`, and
`verify_math.py` (which tests most of this file) never references it either. Genuinely dead,
genuinely harmless, correctly documented as intentionally kept rather than deleted (deleting a
public helper is a signature change). No action needed.

---

### Known open items — resolved against current source

- **read.py:534-620 alleged entity-cache collision, `read_entity()` trusts whatever is
  cached** — **REFUTED**, with live evidence. `read_entity()` (627, 640) goes through
  `cachekey.write_path`/`cachekey.load`, which perform genuine content verification
  (`doc.get("entity") == name`), not just path existence. Tested directly against the real,
  currently-colliding `"Tag Der Toten"` / `"Tag der Toten"` pair on this filesystem
  (`os.path.samefile` proven True for their natural paths): asking `cachekey.write_path` for
  `"Tag Der Toten"` when the natural path is occupied by `"Tag der Toten"`'s file correctly
  falls through to `disambiguated_path` because `owns()` returns `False`. The mechanism works.
  **The live vulnerability is Finding 1 above** — a *different*, unguarded reader of a sibling
  cache (`data/feats`, via `queue()`), not `read_entity()` itself.
- **read.py:327-337 `_ask` runs the whole ladder inside the local gate** — **CONFIRMED**, see
  Finding 2.
- **read.py:~208 stale comment** — **CONFIRMED**, see Finding 4.
- **sevenfold.py:232-238 tautological balance check** — **CONFIRMED**, see sevenfold section
  below (and note it is already self-documented as intentional in the surrounding comment).
- **Transport resolution / worker count vs bucket count** — checked, no bug. `ensure_transport()`
  resolves exactly once under `_TRANSPORT_LOCK` before any worker starts (233-262); the race the
  docstring describes fixing is closed as described. `run()`'s `--workers auto` path derives
  worker count from `data/POOL_PROOF.json`'s live count of buckets with `verdict == "answers"`,
  `+2`, clamped to `[2, 16]` (1092-1100) — a genuine, if approximate, proxy for bucket count, not
  a magic number.

### Other checks that came back clean

- `_names()` (160-191): tested live against both documented false-positive incidents
  (`MetalGarurumon…` vs entity `Garurumon` → `False`; `"The Daily Planet…"` vs entity
  `Lois Lane` → `False`) and against real positives (own name, bare pronoun, inflected plural
  `Xenomorphs` vs `Xenomorph`) — all four returned the documented-correct answer.
- `_HAS_ACTION` (103-110): measured live over 60 randomly sampled `data/feats/*/*.json` files
  (142 real 10,000-char chunks): only 4.9% were skipped as "no action verb," nowhere near the
  historical "0.28% pass rate" regex-gate failure this module's header describes replacing. The
  filter is genuinely generous in practice, not a decorative gate.
- No caps found. `cap_chunks` defaults to `None` (uncapped) and is CLI-opt-in; `--limit` on
  entities is the same pattern already sanctioned elsewhere in this codebase (`--pilot N`); the
  `[:12]` in `main()`'s `--one` printer is provably display-only (the full record is already
  written to disk before that loop runs). `priority()`/`queue()` correctly keep the "thin" bucket
  (Hard Rule 0 fix already landed, per its own extensive comment) rather than dropping it.
- No committed secrets.
- Two-writer contract: read.py never writes to `data/records/*.json`; all its own cache/state
  writes end in `silence.replace_retry` (aside from the temp-naming nuance in Finding 3, which is
  a race concern, not a wrong-writer concern).

---

## src/gpu_lane.py

Read in full. Clean.

- `_alive()`'s Windows `OpenProcess`/`GetExitCodeProcess` path correctly distinguishes "no such
  process" from "exists, not mine" from "unknown" (treated as alive, which is the documented,
  correct-direction default given `_expired()` is the real backstop).
- Claim/slot files are written via `silence.replace_retry`; `_touch()` explicitly refuses to
  resurrect a record belonging to a different or now-absent PID (the exact re-creation bug its
  docstring describes fixing).
- `_remove_retry` retries specifically on transient `PermissionError`, treats `FileNotFoundError`
  as success (already-released), and returns a boolean rather than raising — consistent with the
  module's "fail open" charter.
- `status()` iterates every file under `LANE` with no truncation ("never a sample," honestly so).
- No caps, no tautologies, no dead code, no committed secrets.
- Not a bug, but worth noting alongside read.py Finding 2: `pipeline.ask()` (pipeline.py:373)
  wraps *every* Ollama call — including the ones `read._local_carded` makes — in
  `gpu_lane.lane()`, a second, cross-process arbitration layer on top of read.py's own
  in-process `_GATE_LOCAL`. Both default to the same env-derived slot count
  (`PANSCRIPTUM_GPU_SLOTS`/`OLLAMA_NUM_PARALLEL`), so they're consistent with each other, not
  conflicting — just two independent layers stacking, which is the intended "defence in depth"
  shape for this module.

---

## src/prose_gate.py

Read in full, specifically hunting for a way to defeat it, per the task's critical context. This
is the strongest-built file in the batch.

**Fail-closed checks, verified:**
- `gate_open()` (68-87) and `step4_gate_open()` (90-116) both use `cfg.get(key, False) is not
  True` — strict identity, not `bool()` — and both fail closed on: an unreadable/missing
  `config.yaml` (caught `Exception`), a config that parses but isn't a mapping (e.g. a bare
  string or list), and any non-`True` value including quoted `"false"`, quoted `"true"`, and
  `1`. Cross-checked against `drill.py`'s own adversarial test battery (lines 95-106), which
  specifically drills all of these cases plus the real `True` case.
- `evidence_ok()` (163-194) additionally hardens the floor itself: a non-numeric floor, or a
  floor outside `(0, 1]` (including exactly `0`), is treated as **misconfigured** and refuses
  everything — closing the specific historical hole where `prose_min_cited_fraction: 0` would
  have silently disabled the whole layer.
- `cited_fraction()`/`evidence_ok()` return "unknown" (→ refuse) for a source absent from
  `COVERAGE.json`, a source with `entries: 0`, or an unreadable `COVERAGE.json`.
- `cited_names_for()` (289-327) fails closed to an **empty set** (nothing cited) on any read
  error against `WIKI_HOSTS.json` or the cache — the safe direction, since an empty cited set
  makes every axis score "unearned" and refuses the block, rather than admitting one.

**Cross-file check on the specific incident CLAUDE.md names** ("the `bool()` bug", a second,
looser implementation of the same check): grepped every reference to `prose_enabled` across
`src/`. `overnight.py:_prose_enabled()` used to reimplement the check with
`bool(cfg.get("prose_enabled", False))` — its own docstring records the incident (measured: `1`,
`"1"`, `"true"`, `"no"`, and **`"false"`** all opened that looser check). **Current code no
longer reimplements it** — `overnight.py:52` now delegates: `return prose_gate.gate_open()[0]`.
No other second implementation of any of the four layers exists anywhere else in `src/`;
`generate.py` calls `PG.assert_gate_open`, `PG.evidence_ok`, `PG.assert_block_complete`,
`PG.cited_names_for`/`unearned_instrument` directly rather than reimplementing any of them
(verified by reading generate.py's call sites at lines 303-320, 349, 395).

**Defeat vectors tried and found closed:**
- Line-anchored regexes (`section_shortfall`'s field check, `_AXIS_RE`) require the label at the
  *start of a line* (with markdown decoration explicitly skipped), which is the fix for the
  documented "single run-on sentence that merely mentions all four labels" defeat.
- `MIN_ENTRY_BODY_CHARS = 120` closes the "four bare labels, zero prose" stub defeat.
- `SECTION_LOSS_FLOOR = 0.0` is genuinely zero-tolerance: `frac < (1.0 - 0.0)` fails on *any*
  missing required section, not just a majority.
- Ghost entries (manifest asked for an entry, none arrived) and extra entries (model invented
  more than asked) are both counted against the block, not just the first case.
- The six-axis vocabulary `_AXIS_RE` checks (`Strength, Dexterity, Constitution, Intelligence,
  Wisdom, Charisma`) was cross-checked against `prompts/system_style.txt:140-141` — the "Instrument"
  section's actual spec — and matches exactly, so the regex is targeting the right thing.

**FINDING 6 — MEDIUM — robustness gap, fails in the safe direction only:** `unearned_instrument()`
(330-347) extracts an entry's name from its first line with `head.strip().strip("*").strip()` —
this strips only whitespace and literal `*` characters. A heading using other markdown decoration
(`#`, `_`, a numbered-list prefix) would leave `name` un-normalized, fail to match the entity in
`cited_names`, and cause a **false positive** "unearned instrument" refusal for a genuinely
well-cited entity. This cannot be used to defeat the gate open — it fails toward *more* refusal,
not less — but it's a real correctness gap next to `section_shortfall`'s more careful
decoration-stripping regex, and could needlessly halt legitimate generation. Suggested fix: reuse
the same `^[\s*_#>-]*` stripping approach already used elsewhere in this file.

**Verdict:** could not find a way to make `prose_enabled: false` (or any oddly-typed/missing/
corrupt config) open the gate. No second, looser implementation exists anywhere it matters. The
one real gap found (Finding 6) is a false-refusal risk, not a false-open one.

---

## src/sevenfold.py

Read in full.

**FINDING 7 — MEDIUM — REPRODUCED (code trace) — a check that cannot fail, but honestly labeled as one**

**Where:** `main()`, lines 229-246, specifically:

```python
ok = "OK" if hi <= SPAN else "OVER SPAN"
```

`seams()` (108-129) clamps every parent's child count to `k = max(1, min(span, len(block)))`,
i.e. at most `span` children, by construction — so `hi <= SPAN` is a mathematical certainty for
any input and `"OVER SPAN"` can never print. This is, unusually, already flagged in the comment
immediately above it (241-244): *"`seams()` already clamps every child count to SPAN, so 'OVER
SPAN' cannot print for any input. This displays a GUARANTEE, not a discovery... it becomes a real
check only if `seams()` ever stops clamping."* So this is an honest, self-aware dead check, not a
hidden defect — flagged here anyway per the audit's "checks that cannot fail" lens, since the
report format the printout produces (`OK`/`OVER SPAN` per tier) reads to anyone who hasn't read
the source as if it were live verification. **Suggested fix:** either drop the branch (print the
range without a verdict), or turn it into a real check in `verify_math.py`/`drill.py` that
actually varies `span` past what a block can support and confirms the clamp holds — which is
exactly what the comment says would make it meaningful.

**Otherwise clean:** `affinity_order` (greedy nearest-neighbour, documented non-optimal by
design), `shelve`'s weakest-seam cutting, the two-stage source/world shelving in `build()`, and
`shelfmark()`'s tier-presence-only rendering all read correctly against their own stated intent.
No caps (`build()` processes every source and every world unconditionally; the `[:8]` sample
prints in `main()` are provably display-only, after the full `coords`/`worlds` dicts are already
built). The one shared-state write (`SEVENFOLD.json`) correctly uses `silence.write_json`. No
dead code, no committed secrets.

---

## src/autostart.py

Read in full. Clean, one benign race noted for completeness.

- `_twin_watchdog()` (121-145) has a small TOCTOU window: two watchdog processes starting near-
  simultaneously could both see no twin and both proceed. **Confirmed benign**: `overnight.py`
  self-guards against a duplicate supervisor launch (`running("overnight.py")` check at
  `overnight.py:610`), so a second `start_supervisor()` call from a second watchdog is a no-op,
  not a live double-supervisor. Noted, not raised as a finding.
- `supervisor_alive()` (94-100) calls `overnight.running("overnight.py")` with the default
  `include_self=False` from a *separate* watchdog process — this is the documented-correct usage
  of that flag (the footgun `running()`'s own docstring describes is same-process self-reporting,
  e.g. `dashboard.py`/`publish.py` computing their own status, which is not what's happening
  here).
- VBS launcher construction (`_vbs_body`, 56-76) correctly uses `Chr(34)` doubling rather than
  nested quotes, matching its own comment about VBScript having no escape character; window
  style `0` (hidden) is passed to `sh.Run`, consistent with the "no console windows" convention
  already established elsewhere on this machine.
- `start_supervisor()` correctly passes `CREATE_NO_WINDOW | DETACHED_PROCESS` for the child.
- No caps, no two-writer-contract writes (log files here are append-only diagnostics, not
  parsed-back shared state, so the `silence.replace_retry`/`write_json` contract doesn't apply to
  them), no committed secrets, no dead code found.

---

## src/catalogue_aurora.py

Read in full.

### FINDING 8 — MEDIUM — REPRODUCED (isolated repro) — a denied write is still counted as written in the run's own summary

**Where:** lines 140 vs 150-153:

```python
written.append((r, record))                     # unconditional
if not args.dry_run:
    import pipeline as _P
    if not _P.write_record_catalogue(
            os.path.join(RECORDS, slug(source_name) + ".json"), record):
        print(f"      -> WRITE DENIED {source_name}; roll left untouched", flush=True)
        continue
    r["entry_count"] = len(entries)
    r["status"] = "catalogued"
```

`written.append` happens before the write-success gate. The gate correctly protects the *roll*
mutation (`r["entry_count"]`/`r["status"]` are only set after a successful write — this is the
exact fix the adjacent comment, lines 143-149, describes landing for the roll). It does **not**
protect the `written` list, which drives the final summary print (161-165). A denied write is
still tallied into `"Wrote N records from Aurora XML"` and its full (unwritten) entry count is
printed in the per-source breakdown.

**Reproduced** with an isolated script mimicking the exact control-flow shape (two sources, one
write denied, no real files touched):

```
      -> WRITE DENIED B; roll left untouched
Wrote 2 records from Aurora XML (claimed)
  2 entries A
  3 entries B
```

Source B's denial is printed, then immediately contradicted by the summary claiming it was
written with 3 entries.

**Why it matters:** this is the same failure shape ("a swallowed failure lands in exactly the
shape the design trusts," per `silence.py`'s own charter) as the bug fixed one screen above it
for the roll — the fix just wasn't applied to the console-facing tally, which is precisely what
an owner or supervisor log-reader would trust as "did the run's own report understate or overstate
what happened." No data corruption results (the roll and the on-disk record are both correctly
left in their prior state), so this is a reporting-accuracy bug, not a data-integrity one.

**Fix:** move `written.append((r, record))` to after the write-success check, or track denied
writes in a separate list and subtract/report them explicitly.

### Other checks

- No Hard Rule 0 violation: `parse_folder()` iterates every `*.xml` file recursively and every
  `<element>` in each, with no cap; the only truncation (`slug()`'s `[:60]`) is a filesystem-safe
  filename cap, not a roster truncation.
- Per-file XML parse failures are caught, logged via `silence.note`, and skip only that file —
  documented and reasonable ("a malformed homebrew file should not abort the whole source").
- LOW/HYPOTHESIS, not verified live: `by_name = {r["name"]: r for r in roll}` (109) would
  silently keep only the last row on a duplicate `name` in `SWEEP_ROLL.json`. No duplicate was
  found in the current roll; flagged only as a latent shape, not a live bug.
- Two-writer contract: fully compliant. Records go through `pipeline.write_record_catalogue`
  (the catalogue's own writer, correctly gated on its return value for the roll mutation); the
  shared roll itself is written via `silence.write_json` (line 159).
- No committed secrets.

---

## Summary of severities

| # | File | Finding | Severity | Status |
|---|------|---------|----------|--------|
| 1 | read.py | `queue()` bypasses cachekey, live NTFS collision confirmed | HIGH | REPRODUCED |
| 2 | read.py | `_ask` throttles the whole cascade ladder to GATE_LOCAL_N under local regime | HIGH | REPRODUCED |
| 3 | read.py | `_save_qcache`/`read_entity` write use unscoped tmp names, unlike `_chunk_put` | MEDIUM | REPRODUCED (code cmp.) |
| 4 | read.py | stale "GPU is last resort" comment contradicts the ladder actually implemented | LOW | REPRODUCED |
| 5 | read.py | `cache_path()` confirmed dead, correctly self-documented | INFO | REPRODUCED |
| 6 | prose_gate.py | `unearned_instrument` name-strip misses non-`*` markdown, false-positive refusal risk | MEDIUM | HYPOTHESIS (logic read, not exercised) |
| 7 | sevenfold.py | `OVER SPAN` branch is tautological, already self-documented as such | MEDIUM | REPRODUCED |
| 8 | catalogue_aurora.py | denied write still counted in the run's own summary | MEDIUM | REPRODUCED |

No HIGH findings in gpu_lane.py, prose_gate.py, autostart.py. No Hard-Rule-0 cap violations
anywhere in this batch. No committed secrets anywhere in this batch.

**On the critical context:** `prose_gate.py`'s four layers all fail closed on unreadable/missing/
oddly-typed config, and the specific historical second-and-looser implementation
(`overnight.py`'s `bool()` check) is confirmed already fixed by delegation, not by parallel
patching. The gate could not be defeated by anything tried here.
