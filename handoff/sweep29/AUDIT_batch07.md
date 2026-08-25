# BATCH 07 AUDIT — run29

Modules: `src/magnitude.py`, `src/allsweep.py`, `src/address_space.py`, `src/feats_index.py`,
`src/propagation.py`, `src/cosmology_graph.py`

Every module was read in full, line by line. Several findings were reproduced end-to-end with
small driver scripts run under the miniconda python (scripts kept in the session scratchpad,
not in the repo). `magnitude.py` grew from 1046 to 1109 lines mid-audit — the supervisor is
actively editing it this run (consistent with the pre-briefed CHARTER_REGRESSION.json
checkpoint fix). I re-read the file after the shift and re-verified line numbers below against
the current on-disk state. The known `calibrate()` single-write issue is confirmed already
fixed in the live file (checkpoints via `_land()` after every benchmark, `at` stamped only on
`complete`) — not re-reported.

---

## 1. `src/magnitude.py`

### 1.1 Correctness bug — guard 3 (SUBJECT) is entirely absent from the split-assay path — **REPRODUCED**

`verify()` (the one-shot gate, lines 335–400) applies five checks including guard 3 SUBJECT at
line 392:

```python
if P._PATIENT.search(text) or _HANDOFF.search(text):
    rejects.append((ax, f"entity is not the actor: {text[:60]}"))
    scores[ax] = A.UNESTIMABLE
    continue
```

`_HANDOFF` (defined lines 196–199) is this module's own answer to the file's own motivating bug,
documented in the module docstring (lines 12–23): "Goku summoned Zeno, who erased the rogue Kai"
— a sentence about Goku that is really Zeno's deed.

`_split_gate()` (lines 572–590), used for every entity assayed via the split path, checks only
verbatim containment:

```python
if isinstance(sc, (int, float)) and ft and any(ft in o for o in own):
    scores[ax] = max(0.0, min(9.9, float(sc)))
    sheet[ax] = ft
```

There is no `_PATIENT` or `_HANDOFF` check anywhere in `_split_gate`. The docstring's claim that
"Axis-relevance is by construction" is true for guard 2 (RELEVANCE — the candidate lists are
already axis-partitioned by `feats.by_axis`), but guard 3 (SUBJECT) has nothing to do with which
axis a sentence was filed under, and is not "by construction" at all — it is simply skipped.

`feats.by_axis()` (`src/feats.py:704-727`) filters out `P._PATIENT` matches (passive-voice
patient sentences) at mining time, but does **not** filter `_HANDOFF`-style active-voice handoff
clauses — that filter exists only inside `magnitude.verify()`. So a handoff sentence can and does
survive into the candidate lists that both paths consume.

The split path is explicitly the path used for "the heaviest, best-documented entities in the
library" (module docstring, lines 455–462) — i.e., precisely the entities richest in exactly the
kind of multi-actor sentence `_HANDOFF` exists to catch.

**Reproduction** (organic end-to-end, using the project's own `feats.by_axis` miner and
`magnitude`'s own gate functions, no fabricated internals):

```
sentence = "Goku summoned Future Zeno, who erased the rogue god from existence."
F.by_axis(sentence, "test-page") -> mines cleanly into 'ruin' AND 'transgression'

Split-path _split_gate() on 'transgression', score 9.0:
  -> {'transgression': 9.0}   rejects: []          # ACCEPTED, full score, no rejection

One-shot verify() on the same citation:
  -> unestimable   rejects: [('transgression', 'entity is not the actor: Goku summoned
     Future Zeno, who erased the rogue god from exi')]   # correctly REJECTED
```

**Consequence:** entities assayed via the split path (the largest, most heavily-evidenced entries
in the library — Goku, Vegeta, Frieza-class entities per the module's own worked example) can
receive scored, published axis values built on evidence that belongs to a different actor in the
sentence, with the file's own headline defect (Zeno's erasure filed under Goku) able to recur
undetected specifically for the entities where it is most likely to occur.

### 1.2 Concurrency — fixed-name `.tmp` files, lock is per-process only — **VERIFIED-BY-READING / HYPOTHESIS for actual collision**

`run_batch()` (writes `OUT + ".tmp"`, currently line ~1050) and `calibrate()` (writes
`_cr + ".tmp"`, line 848) both use a **fixed temp filename**, and the only synchronization is a
`threading.Lock` inside `run_batch()`'s worker closure — which protects against races between
threads in the *same* process, not between two separate OS processes. If two `magnitude.py
--batch` invocations (e.g. split by `--host` to parallelize, which the CLI explicitly supports)
or a `--batch` run overlapping a `--calibrate` run were ever launched concurrently, both could
write to the same `.tmp` path and one process's write could be clobbered or read half-written by
the other's `os.replace`.

Checked live orchestration: `src/foreman.py` only ever starts `magnitude.py --calibrate` (line
~665), never `--batch`, and only one instance. So this is a **latent** risk, not something I can
show currently firing — flagging as HYPOTHESIS/dormant, not a live defect, but the code has no
defense if a future runbook (or a person by hand) ever runs two batches side-by-side by host.

### 1.3 Everything else in magnitude.py

- `candidates(ev, cap=None)` (line 415) and `compose(..., budget, ...)` (line 524): both are
  correctly uncapped in every current call site — `candidates()` is never called with `cap`;
  `compose()` is always called with `budget=None` (line 610), so `dropped` is always 0, exactly
  as the comment at the `evidence_dropped_to_fit` field says. No live Hard-Rule-0 violation, but
  the `cap`/`budget` parameters are dead machinery that would silently truncate if ever wired up
  — worth removing or guarding, not a current bug.
- `queue(host=None, limit=None)` (line 904): `limit` is an explicit opt-in CLI parameter,
  defaults `None` (uncapped). Not a violation.
- `saturated()`, `quantity_scores()`, `host_ceiling()`, `settled()`: read cleanly, do what they
  claim, correctly distinguish "no evidence" / "saturated" / "deferred" (verified by reading
  `settled()`'s three-way classification against `run_batch`'s resume logic).
- The Windows `os.replace` retry loop in `run_batch()` (5 attempts, 0.3s*n backoff) is a
  reasonable mitigation for the WinError 5 reader-collision the comment describes; no issue found.

---

## 2. `src/allsweep.py`

### 2.1 Correctness bug — IMPORT tier misclassifies a deliberate `raise SystemExit(...)` guard as healthy — **REPRODUCED**

`check_import()` (lines 98–119):

```python
ok = r.returncode == 0
err = ""
if not ok:
    tail = (r.stderr or "").strip().splitlines()
    err = tail[-1][:150] if tail else f"rc={r.returncode}"
    if "Traceback" not in (r.stderr or ""):
        ok, err = True, "no CLI (imported cleanly)"
```

The intent (per the comment) is: a module with no argparse exits nonzero on `--help`, which is
not a fault, and only an unhandled exception (visible as a `Traceback` in stderr) is a real
crash. But an uncaught `SystemExit(message)` — exactly the pattern `magnitude.py` and
`allsweep.py` **themselves** use for their own source-corruption guard —

```python
raise SystemExit(__file__ + ': a regex escape was eaten in transit ...')
```

exits nonzero and prints its message to stderr **without** a `Traceback` line (Python's top-level
handler special-cases `SystemExit`). So the exact class of self-check this project relies on to
catch corrupted source is invisible to `allsweep`'s own IMPORT tier — it is graded `ok: True,
"no CLI (imported cleanly)"`, the identical verdict a perfectly healthy module gets.

**Reproduction**, using `allsweep.check_import()` itself, unmodified, against a one-line module:

```python
# corrupted_mod.py
raise SystemExit("corrupted_mod.py: a regex escape was eaten in transit - repair before running.")
```
```
>>> allsweep.check_import("corrupted_mod")
{'module': 'corrupted_mod', 'ok': True, 'detail': 'no CLI (imported cleanly)', 'seconds': 0.9}
```

**Consequence:** this is the audit tool that exists specifically to catch "a module nobody has
invoked since it was edited is a module nobody knows is broken" (module docstring, line 26). A
module that trips its own `_BAD_CHARS` corruption guard, or any other deliberate
`raise SystemExit("error: ...")` at import time, passes the IMPORT tier silently. This is a
check-that-cannot-fail in the lens-4 sense for this specific failure class: the tool designed to
catch exactly this defect reports it as clean.

The `and "local variable" in ln and "referenced before" in ln` guard mentioned as a suspicious
precedence at first glance (line 362 in the lint tier) was checked and is **correct** —
`and` binds tighter than `or` in Python, so the intended `undefined OR (local-var AND
referenced-before)` reading is what actually executes. Not a bug.

### 2.2 Everything else in allsweep.py

- The lint tier's newly-added `lint` key and the "RECONCILE deliberately does not count" honesty
  note (lines 440–454) are self-aware and consistent with what the code does — no
  comment/code contradiction found there.
- `reconcile()`'s seven checks were read individually; each does what its comment claims
  (band-ceiling comparison uses an ordinal index lookup correctly at line 270–272; the
  process-roster check correctly reads from `overnight.ALL_JOBS` rather than a hand-kept list,
  per the comment at line 300–306, and I confirmed `overnight.ALL_JOBS` exists and is imported
  live, not hardcoded).
- Minor, unconfirmed: the "MORE THAN ONE INSTANCE RUNNING" check (line 300–316) does
  `job in ln` substring matching against the process command-line list; if one job name is ever a
  substring of another (none currently are, checked against `overnight.ALL_JOBS`), this would
  double-count. HYPOTHESIS only, no current collision found.
- `silence.write_json` is used for the final `ALLSWEEP.json` write (atomic replace-with-retry per
  the comment) — consistent with the two-writer/atomic-write contract for shared state files.

---

## 3. `src/address_space.py`

### 3.1 Formatting bug — `citation_card()`'s assay string has no defence against `decimal == 1.0` — **REPRODUCED (isolated), not yet observed in production data**

`citation_card()` (lines 186–213) builds the printed assay string at line 206:

```python
f"𝔄 {band}" + (f".{int(round(decimal*100)):02d}" if decimal is not None else "")
```

with no upper-bound check on `decimal`. `assay.py`'s own `assay()` (its source of `decimal`,
not in this batch but the direct producer of the value this function formats) clamps `_dec` to
`0.99` only when the **unrounded** composite is `>= 1.0` (its lines ~437-444); if the unrounded
value lands in `[0.995, 1.0)`, the clamp check (`_dec >= 1.0`) is `False`, but
`round(_dec, 2)` still yields exactly `1.0`, and that `1.0` is what gets stored as `decimal` and
handed to `citation_card()`.

**Reproduction** of the underlying arithmetic:

```
_dec = 0.996
_dec >= 1.0            -> False   (clamp does not fire)
round(_dec, 2)          -> 1.0
citation_card's format: int(round(1.0 * 100)):02d -> "100"   ->  "𝔄 M4.100"
```

This produces a malformed three-digit decimal in the printed citation card (and in `assay.py`'s
own `moth_number`, which uses the identical unguarded `int(round(decimal*100)):02d` pattern).

Checked the live `data/ASSAYS.json` (507 records): 7 records currently sit at exactly the clamped
ceiling `0.99` (Goku Jr., Picard, Janeway, Monkey D. Dragon, Cuba, Farsight, Lysithea) — real
confirmation that the ceiling condition (every scored axis maxed) does occur in practice — but
none currently show the `0.995–0.999999` slipped-clamp value, so the exact `.100` artifact has
not yet appeared on disk. This is a narrow floating-point window and it is real and reachable;
`citation_card()` has no independent defence even though it is the function that actually prints
the string a reader sees.

### 3.2 Everything else in address_space.py

- `pack()`/`unpack()`/`FIELDS`/`WIDTHS`: bit-width derivations verified against the header
  docstring's cited censuses (galaxy 2.0e11 → 38 bits, star 1.0e8 → 27 bits, planet 1.6 → 1 bit
  all check out arithmetically). `pack()` raises rather than silently wrapping/truncating an
  out-of-range field — correct per its own stated rationale.
- Lens 7 (comment/code mismatch), minor: the "THE WIDTHS ARE DERIVED, NOT CHOSEN" table (lines
  29–39) lists only 5 fields (hyperverse/universe/galaxy/star/planet) and is a holdover from
  before xenoverse/metaverse/multiverse were added as their own tiers (the "CORRECTED against
  Part Two" section immediately below it, lines 75–105, supersedes it). The two sections describe
  different eras of the design and are not actually contradictory once read together, but the
  older table is stale and could mislead a skim-reader about how many bits/fields exist today.
  Not a functional bug — flagged for documentation cleanup only.
- `assign()`, `seed_from_card()`, `map_seed()`: read correctly; the identity/measurement split in
  `citation_card()` and the deliberate exclusion of the measurement half from the seed key are
  implemented exactly as their docstrings describe.
- `main()`'s demo/round-trip and `WORLDSEEDS.json`/`TIERS.json` catalogue pass: no caps, no
  truncation; `silence.write_json` used atomically for `SHELFMARKS.json`.

---

## 4. `src/feats_index.py`

### 4.1 Correctness bug — silent evidence loss on same-source name-normalization collisions — **REPRODUCED with real data**

`feats_for_source()` (lines 166–209) builds its name lookup with:

```python
entries_by_norm = {}
for e in (record.get("entries") or []):
    entries_by_norm.setdefault(_norm(e.get("name")), e)
```

`setdefault` means: if two distinct catalogue entries in the *same* source normalize to the same
key (alphanumeric-fold, per `_norm`'s own documented lossiness re: punctuation/spacing/parens),
only the **first** one encountered keeps the slot. Any feats record whose entity name matches
that normalized key attaches only to that first entry; the second, equally-real catalogue entry
silently receives zero feats evidence from this join — no warning, no count, nothing in `audit()`
that would surface it (the collision is inside one source's own entry list, not between sources).

**Reproduction**, scanning every source's real catalogue via `pipeline.records()`:

```
sources scanned: 210
normalization collisions (distinct names -> same norm key): 22
  Marvel            'fortkrakoa' <- ['Fort (Krakoa)', 'Fort Krakoa']
  League of Legends 'belveth'    <- ["Bel'Veth", 'Belveth']
  all Battlefield   'avantisavoia' <- ['Avanti Savoia', 'Avanti Savoia!']
  ... (22 total across 12 sources)
```

Direct confirmation for Marvel:

```
entries with norm 'fortkrakoa' in raw list: ['Fort (Krakoa)', 'Fort Krakoa']
entries_by_norm['fortkrakoa'] resolves to only: Fort (Krakoa)
```

So `Fort Krakoa` (the second entry) can never receive feats evidence through `feats_for_source`,
even if `readfeats/` genuinely holds mined deeds under that name — they are routed to `Fort
(Krakoa)` unconditionally, or dropped if the mined entity name normalizes closer to the other
form. 22 known instances today; likely to grow as the catalogue does, since it's purely a
function of near-duplicate/alias naming already present in the catalogue.

This is not the ordered-listing truncation Hard Rule 0 targets, but it is the same family of
fault: a completed-looking join (98.6% quoted in the module's own docstring) that quietly
discards real evidence for specific entries in the same shape as a successful join, with the
loss invisible to `audit()`.

### 4.2 Everything else in feats_index.py

- `_norm()`'s docstring was itself corrected 2026-08-24 (per its own text) to stop claiming a
  capability it doesn't have; checked against the code and the docstring is now accurate.
- `host_to_sources()`, `load_index()`, `audit()`: all read/behave as documented; the `pages:`
  sentinel is correctly excluded from the host inversion (line 126) so it can't collide into a
  single pseudo-host.
- `feats_for_source()`'s final sort (`-r["feat_count"], r["entity"]`, line 208) is a ranking, not
  a truncation — nothing after it drops elements. No caps anywhere in this module; the docstring's
  "NO CAPS" claim (line 62) holds.

---

## 5. `src/propagation.py`

Read in full. No caps, no truncation, no swallowed-exception issues (the module does not
catch/silence anything — it's a pure read+compute path over `SHARED_STAGE_GRAPH.json`). Dijkstra
implementation in `shortest()` is standard and correct (early-exit on reaching `dst`, proper
`seen`-set guard against re-processing, `prev`-chain reconstruction). `observed_mark()`'s two
independent clocks (own-ascension vs arrival-lag) match the docstring's stated correction of the
prior (summed) bug. No findings in this module by itself — but see §6.1, which materially affects
what this module's `shortest()` sees as connected, since it consumes cosmology_graph.py's output.

---

## 6. `src/cosmology_graph.py`

### 6.1 HARD RULE 0 — the persisted graph silently drops 71% of computed source-pairs and disconnects 25 sources entirely — **REPRODUCED with real data**

`main()`'s `--write` path (lines 143–155):

```python
"pairs": [{"a": a, "b": b, "weight": round(w, 3), "shared_sample": pair_shared[(a, b)]}
          for (a, b), w in sorted(pair_w.items(), key=lambda kv: -kv[1])
          if w >= 1.0],
```

`w >= 1.0` is an unexplained magic-number threshold applied to the **data written to disk**
(`data/SHARED_STAGE_GRAPH.json`), which `propagation.py` and `resonance.py` both read as ground
truth. This is a DATA truncation, not a display one — nothing marks it as a preview, and nothing
downstream is told that pairs below 1.0 existed.

This is the same file that, five lines above (86–92), has an explicit comment describing how it
fixed a **sibling instance of exactly this bug** two days earlier — a `< 8` cap on the per-pair
`shared_sample` list that silently made a ninth shared entity "not exist to anything downstream"
(`resonance.py:146`). The comment credits that fix to "Hard Rule 0, ruled 2026-08-24." The
`w >= 1.0` filter on the **pairs list itself**, three lines below that same comment, was not
touched by that ruling and remains exactly the pattern it describes: a threshold that decides
some of the computed evidence does not exist to any downstream reader.

**Reproduction**, running `build_graph()` (the full, uncapped in-memory computation) and comparing
against what `main()`'s `--write` path would actually persist:

```
total sources with >=1 shared entity : 197
sources appearing in the written graph (w>=1.0 threshold): 172
sources with ALL their pairs below threshold (vanish from written graph): 25
  ['2112 (Rush)', 'DMs Guild: Heroes of Hell', 'DMs Guild: The Great Dale', 'Darksiders',
   'Date A Live', 'Descent into Avernus', 'Extra Life', 'Ghosts of Saltmarsh',
   'KBP Unlikely Heroes', 'Kenichi the Mightiest Disciple', 'Kinnikuman', 'Mage Hand Press',
   'Pantheon: Korean', 'Pantheon: Polynesian', 'Problem Solverz', 'Rainbow Six',
   'Rosario + Vampire', 'Sakamoto Days', 'The Amethyst / Cockroach King screenplay ...',
   'Warhammer Fantasy']

total pairs: 3753   pairs dropped by w>=1.0 filter: 2666 (71.0%)
```

**Consequence:** `propagation.py`'s `shortest()` treats any source not present in `adj` as
categorically disconnected (`math.inf`, empty path) — and `main()`'s own probe loop even has a
branch for "?? not in graph" as an expected outcome. For these 25 sources, `propagation.py` will
report "DISCONNECTED (no shared furniture at any remove)" for every query, which directly
contradicts `propagation.py`'s own stated premise ("two sources sharing nothing are far apart" —
these sources do NOT share nothing; they share weak, real, computed evidence that this threshold
discarded before it ever reached the file). It is a smaller universe wearing the same JSON shape
as the real one, in the same file, in the same run, that already patched a sibling case of this
exact defect.

### 6.2 Everything else in cosmology_graph.py

- `top = sorted(...)[:16]` (line 131), `comps[:8]` (line 140), `c[:6]` (line 141),
  `pair_shared[(a,b)][:4]` (line 134): all confirmed to be **console print previews only**, not
  written to `SHARED_STAGE_GRAPH.json` — correctly DISPLAY truncation, not a Hard Rule 0
  violation.
- `components()`'s connected-components computation (BFS/DFS via explicit stack) is standard and
  correct; the `clusters` field written alongside `pairs` uses the CLI `--threshold` (default 3.0,
  independent of the `w >= 1.0` pairs filter) — that's a separate, intentionally tighter
  clustering pass and is not itself flagged here.
- `silence.write_json` used for the atomic write, consistent with the shared-state-file contract.

---

## Summary of severity

| # | Module | Finding | Status |
|---|--------|---------|--------|
| 1 | cosmology_graph.py | `w >= 1.0` pairs filter silently drops 71% of edges, disconnects 25 sources from SHARED_STAGE_GRAPH.json | REPRODUCED |
| 2 | magnitude.py | `_split_gate()` omits guard 3 (SUBJECT/`_HANDOFF`) — the file's own motivating bug can recur, unblocked, for the heaviest entities | REPRODUCED |
| 3 | allsweep.py | `check_import()` reports a deliberate `raise SystemExit(...)` guard (incl. this project's own corruption guard) as "imported cleanly" | REPRODUCED |
| 4 | feats_index.py | Same-source name-normalization collisions (22 known) silently strand feats evidence on the losing entry | REPRODUCED |
| 5 | address_space.py | `citation_card()`'s decimal formatting has no clamp; a `decimal` of 1.0 (reachable via assay.py's float-rounding edge, not yet seen in production) prints "𝔄 M4.100" | REPRODUCED (isolated) |
| 6 | magnitude.py | Fixed-name `.tmp` files in `run_batch()`/`calibrate()`, lock is per-process only | HYPOTHESIS (dormant — no current caller runs two instances concurrently) |
| 7 | address_space.py | Stale 5-field "WIDTHS ARE DERIVED" table superseded by the later 8-field tier model | VERIFIED-BY-READING (documentation only) |
| — | propagation.py | No findings | — |
