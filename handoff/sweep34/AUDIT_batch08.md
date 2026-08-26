# SWEEP 34 — BATCH 08

Modules read end to end: `src/read.py` (1183), `src/chain.py` (511), `src/custodes.py` (418),
`src/worldseed.py` (339), `src/burgs.py` (269), `src/tells.py` (225),
`src/thread_integrity.py` (184), `src/resync_roll.py` (98).

Nothing under `src/` was edited. Nothing was run that fetches; `read.py --run` was not started.
Every finding below was read out of the source and, where a count is quoted, measured against the
data on disk in this working copy.

Two findings were excluded as already filed, per the batch brief: `thread_integrity.load_entities`'s
crude name fold vs `weave_index.norm`, and `resync_roll` discarding the losing record file silently.

---

## src/read.py

### F1 — stale `silence.note` line tags; two distinct handlers share one tag  (LOCAL, MINOR)

`silence.instrument` generates the tag mechanically as the except-handler's line number:

    call = f'{" " * col}silence.note("{base}:{node.lineno}")\n'      # silence.py:493

Four numeric tags in this file no longer point at their own handler, and `read.py:188` is used at
**two different handlers**, so `health`'s ledger key `silent:read.py:188` merges a failed quick
Cascade attempt with a failed backoff-ladder attempt:

    387:                    silence.note("read.py:188")     # quick pool attempt
    404:                    silence.note("read.py:188")     # backoff ladder attempt
    975:                silence.note("read.py:354")         # queue() record parse
    1012:            silence.note("read.py:379")            # work() wrapper

read.py:188 is in fact a comment line (`# sentence ever written passes the check.`).
Same defect in the other batch files (all verified to point elsewhere):
`chain.py:169 -> "chain.py:91"`, `276 -> "155"`, `283 -> "161"`, `345 -> "252"`;
`worldseed.py:250 -> "248"`, `258 -> "255"`; `thread_integrity.py:56 -> "54"`;
`resync_roll.py:52 -> "45"`. Filed as one order.

### F2 — the "RANKED AND CAPPED" block describes a cap the code no longer applies  (LOCAL, MINOR)

read.py:679-687 still argues for the truncation Hard Rule 0 removed, and states a number
(`twelve`) that appears nowhere in the code:

    679  # RANKED AND CAPPED. Filtering by mention took a shared franchise page from 44 chunks ...
    684  # The cap is depth, not a compromise on it: an entity's own pages run three to twenty chunks
    685  # at 10,000 characters, so twelve covers the whole of most subjects and the densest part of
    686  # every shared page. Uncapped, one entity could eat an hour of GPU on a page that names it

Three lines below, the surviving comment says the opposite, and the code agrees with the second:

    689  chunks.sort()
    691  # is interrupted. Not truncated: a cap here decides on the entity's behalf that the rest of
    694  if cap_chunks:        # None unless a human passes --chunks

The `cap_chunks` parameter itself is fine — no internal caller passes it (`grep` over `src/`:
only `main()` from `--chunks`, default `None`).

### F3 — `_local_carded`'s oversized re-split branch is unreachable, and converts total failure into an empty answer  (RUN, MINOR)

    511  def _local_carded(c, system, prompt, schema):
    514      if len(prompt) <= CHUNK + 2000:
    ...
    525      head, _, body = prompt.partition(chr(10) + chr(10))
    526      merged = {"feats": []}
    527      for i in range(0, len(body), CHUNK):
    528          got = P.ask(c, system, head + ... , schema, timeout=180)
    529          merged["feats"].extend((got or {}).get("feats", []))
    530      return merged

`CLOUD_CHUNK = CHUNK` (read.py:96) and `size = CLOUD_CHUNK if _CASCADE_OK else CHUNK`
(read.py:664), so every prompt is `"ENTITY: " + name + "\nPAGE: " + title + "\n\n" + ch` with
`len(ch) <= 10000`; the else-branch needs `len(name)+len(title) > ~1,983`. The branch is dead, and
the comment above it ("Chunks are built at cloud size ... an oversized passage is re-split here")
describes a size difference that no longer exists.

If it were ever reached it would be worse than dead: every sub-call returning `None` yields
`{"feats": []}`, which is not `None`, so `read_entity` records the chunk as ANSWERED, caches it,
and `if unanswered: return out` never fires — the one guarantee in this file that stops work being
lost permanently. It also never sets `_GPU_DOWN_UNTIL`, so a dead card is not benched on this path.

### F4 — two hand-rolled `path + ".tmp"` writes left behind by the `write_json` migration  (LOCAL, MINOR)

    782      os.makedirs(os.path.dirname(path), exist_ok=True)
    784      tmp = path + ".tmp"
    785      with open(tmp, "w", encoding="utf-8") as f:
    786          json.dump(out, f, indent=1, ensure_ascii=False)
    787      silence.replace_retry(tmp, path)          # read_entity, runs in every pool worker

    906          tmp = QCACHE + ".tmp"                 # _save_qcache

`silence.write_json`'s own docstring names this exact hazard and says the pid+thread temp name is
why: "Two writers of the same path otherwise collide on the temp file itself, and the loser can
replace the winner's target with a partial file -- the same race `read.py:_chunk_put` was already
fixed for individually". `_chunk_put` (read.py:614) carries the fix; these two sites do not, and
`read_entity` is the one that runs under the worker pool with a live daemon on this machine.
`replace_retry`'s verdict is also discarded at 787 (low harm — the entity is simply re-read).

### F5 — `--transport cascade` still falls through to the GPU  (RUN, MINOR)

    346  def _ask_ungated(c, system, prompt, schema):
    348      if _TRANSPORT in ("auto", "cascade"):
    349          if ensure_transport(verbose=False):
    ...
    389              if _TRANSPORT != "cascade" and _GPU_DOWN_UNTIL[0] <= time.time():
    ...
    409              with _FELL_BACK_LOCK:
    410                  _FELL_BACK[0] += 1
    411              if _TRANSPORT == "cascade":
    412                  return None
    ...
    421      return _local(c, system, prompt, schema)

Both guards say cascade mode must never touch the card. But `ensure_transport()` returns False
whenever the bridge import or `CB.engine()` fails (read.py:262), the whole block is then skipped,
and control reaches line 421 — the GPU — under `--transport cascade`. Second defect in the same
lines: the `_FELL_BACK[0] += 1` at 409-410 fires before `return None`, so the progress line's
"(%d to GPU)" counts chunks that were never handed to the GPU on a cascade-only run.

### F6 — `_GATE_STATE` mutated from every pool thread without a lock  (LOCAL, MINOR)

    297  def _gate():
    299      if now - _GATE_STATE["at"] > GATE_RECHECK_S:
    301              import tuning as T
    302              _GATE_STATE["regime"] = T.regime()
    305          _GATE_STATE["at"] = now

`_ask` calls `_gate()` on every model call from up to 16 workers. The read of `["at"]` and the
write at 305 are not atomic together, so at each recheck every in-flight worker passes the test and
calls `T.regime()` — which reads `data/POOL_PROOF.json` and queries `state/cascade_scratch.db`
(`tuning.regime` -> `_answering_buckets` + `cloud_success_rate`). This is the same thundering herd
`ensure_transport`'s own docstring documents fixing ("with ten workers all ten hit it
simultaneously on the first chunk"), and `_TRANSPORT_LOCK` already exists three functions above.
Consequence is duplicated cheap work rather than a wrong value, hence MINOR.

### F7 — `done["skipped"]` is accumulated and never read  (LOCAL, MINOR)

    1004  done = {"n": 0, "feats": 0, "fab": 0, "chunks": 0, "skipped": 0, "unanswered": 0}
    1021          done["skipped"] += out["chunks_skipped"]

`grep -n skipped src/read.py` shows no other use: the progress line at 1046 prints feats, fab,
chunks, `_FELL_BACK[0]` and unanswered, and the closing line prints feats and fab. The number is
computed per entity, summed under the lock, and thrown away.

---

## src/chain.py

Read end to end. The two things this file was fixed for today hold up:
`local_unmatched` is merged inside `with lock:` (368-369) and every other shared structure
(`edges`, `prov`, `done`) is mutated only there; `write_result` and the harvest index both go
through `silence.write_json` and both report the verdict (120-123, 200-204).

Checked and found sound, so recorded here rather than filed: `main()`'s unconditional
`res['deviance_per_df']`, `res['undefeated']` and `res['winless']` accesses (483-486) cannot
`KeyError` or format-crash — `rigor.bradley_terry` always populates them before any refusal branch
(`rigor.py:418-423`), and it is `strengths` alone that is nulled.

Only finding: the stale note tags at 169/276/283/345, filed under F1.

---

## src/custodes.py

### F8 — `_ATT_BASE` is the duplicate table its own comment forbids  (RUN, MINOR)

    221  # DERIVED from assay()'s own attestation table rather than restated. A second hand-written
    222  # table of evidence quality would be a duplicate mechanism for a quantity the charter has
    224  # -- ... and it would drift the moment either copy was edited.
    229  _ATT_BASE = {"Witnessed": 0.10, "Instrumented": 0.08, "Transcribed": 0.20,
    230               "Reconstructed": 0.40, "Disputed": 0.55}

`assay.py:964`:

    floor = {"Witnessed": 0.10, "Instrumented": 0.08, "Transcribed": 0.20,
             "Reconstructed": 0.40, "Disputed": 0.55}.get(attestation, 0.30)

Character-for-character the same five numbers, written twice. What is derived is
`ATTESTATION_QUALITY` from `_ATT_BASE`; `_ATT_BASE` itself is the second hand-written copy the
comment says must not exist, and it cannot currently be imported because `assay`'s copy is an
anonymous literal inside `interval_from_hands` rather than a module constant. Values agree today,
which is exactly the state a drift hazard is in before it drifts.

Not filed, verified instead: `covers_every_reading` (line 344) is a check that cannot fail, and
the comment at 335-343 already says so at length and gives the reason for keeping it. Deliberate.
The Kenshiro numbers in the docstring (`M3.53 ± 0.11`) and in `main()` (`charter: M3.52 ± 0.12`)
are both correct and are different columns of the same charter row —
`reference/keystone_volumes/0-5_DE_CONSONANTIA.md:261`.

---

## src/worldseed.py

### F9 — an era/condition vocabulary the feature extractor can never produce  (OWNER, MINOR)

    183          "size": {"spacefaring": 90, "industrial": 70, "magical": 55,
    184                   "medieval": 45, "primitive": 35}.get(f["tech"], 50),

`f["tech"]` comes from `_first(TECH, ...)`, which returns a name from `TECH` on the attested path
and `table[pick][0]` on the seeded path. `TECH` (worldseed.py:95-100) has exactly four entries:
spacefaring, industrial, magical, medieval. `"primitive"` is unreachable. Same key, same dead
branch, in `burgs.largest_city`:

    122      base = {"primitive": 2500, "medieval": 20000, "magical": 25000,
    123               "industrial": 400000, "spacefaring": 3000000}.get(era, 20000)

and `"settled"` in both of burgs' condition tables (116, 124) is unreachable for the same reason —
`CONDITION` (worldseed.py:90-94) holds only ruined/wartorn/thriving, and the only producers of
`era`/`cond` are `worldseed.features()` (`burgs.main:207`, `navtree.py:51-53`). `genre.py:57`
does carry `tech="primitive"` in its genre priors, but nothing outside `genre.py` reads `priors`
(`grep -rn "priors" src/`), so the wider vocabulary reaches no consumer. Whether the answer is a
`primitive`/`settled` cue row or deleting the dead keys is a curatorial call.

### F10 — `unreachable_by_url` has no callers  (RUN, MINOR)

    236  def unreachable_by_url(opt):

`grep -rn "unreachable_by_url" src/` matches only its own definition (and the stale .pyc). It is a
public helper, so this is a deletion decision rather than a mechanical one; the sibling case
`read.cache_path` was kept deliberately and says so in its docstring, this one says nothing.

### F11 — `worlds[0]` unguarded after an empty build  (LOCAL, MINOR)

    297      print(f"\nworlds encoded: {len(worlds):,}")
    ...
    315      print("     " + to_fmg_query(worlds[0])[:150])

and the same shape in `burgs.main`:

    220      w0 = worlds[0]

`build_all` returns `[]` whenever no catalogued `Places` entry matches `WORLD` — the run prints
"worlds encoded: 0" and then dies on an IndexError several lines later. Note `addrs` two lines
earlier is already defended with `max(1, len(addrs))`, so the guard was on someone's mind.

---

## src/burgs.py

### F12 — two floors for one fact: `HAMLET_FLOOR = 40` vs the literal `30`  (RUN, MINOR)

    93   HAMLET_FLOOR = 40      # "The smallest thing the record still calls a burg. Below this it
                               #  is a farmstead and the catalogue has nothing to say about it."
    114      n = int((p1 / HAMLET_FLOOR) ** (1.0 / ZIPF_Q))
    116      factor = {"ruined": 0.3, "wartorn": 0.8, "settled": 1.0, "thriving": 1.15}.get(...)
    117      return max(3, int(n * factor))
    156          pop = max(30, int(p1 / (k ** ZIPF_Q)))

With `ZIPF_Q = 1.0` the rank-size tail reaches `p1 / n`. For a thriving world `n = 1.15 * p1/40`,
so the smallest burgs come out at `40/1.15 ≈ 34.8` — below the constant that defines what a burg
is, and clamped by a second, differently-valued floor written as a literal. `GENERATORS` is now
genuinely consumed (line 228), so the comment at 75-84 is accurate.

---

## src/tells.py

### F13 — the pattern named "it's not X, it's Y" cannot match "it's not X, it's Y"  (LOCAL, MINOR)

    81   "it's not X, it's Y": r"\b(?:is|was|are|were)n['’]?t (?:a |an |the )?\w+[,;] (?:it|they|which) (?:is|was|are|were)\b",
    82   "X is not Y; it is Z": r"\bis not (?:a |an |the )?\w+[;,] (?:it|which) is\b",

Measured with `tells.scan`:

    "It isn't a fortress, it is a prison."          -> {"it's not X, it's Y": 1}
    "It is not a fortress, it is a prison."         -> {"X is not Y; it is Z": 1}
    "It's not a fortress, it's a prison."           -> {}
    "It's not that it failed, it's that nobody looked." -> {}

Both halves of the contracted form escape: `'s not` is neither `is not` nor `isn't`, and the
completion side accepts only `it is`/`which is`, never `it's`. The undetected form is the one this
module's own docstring names as the shape to catch — line 18: `"It's not that X, it's Y"`.

Checked and clean: `_anchor`'s `pat[4:]` correctly strips exactly `^\s*` (4 chars); the control
character guard at 149-151 is a real check; total patterns is 138, which agrees with the claim in
`pipeline.py:1462`. The lexical overlaps (`myriad`/`myriad of`, `shrouded in`/`shrouded in
mystery`, and the six stem/inflection pairs) do double-count one occurrence under two keys, but
`style_audit` reports per-key rates rather than a sum (`style_audit.py:157-160`), so nothing is
inflated. Not a defect.

---

## src/thread_integrity.py

### F14 — DANGLING only fires when EVERY shared key has drifted  (RUN, MINOR)

    109              gone = [k for k in shared if k not in ents.get(a, ()) or k not in ents.get(b, ())]
    110              if gone and len(gone) == len(shared):
    111                  out["DANGLING"] += 1

The docstring promises the singular: "DANGLING is computed for real, against the live records: a
candidate key whose source no longer holds that entity (weave drift)". Measured against the live
`data/WEAVE_CANDIDATES.json` and `data/records/` in this working copy:

    pairs considered 3753   full-dangling 592   partial-dangling 417   clean 2744

So 417 pairs carry at least one candidate key whose source no longer holds that entity, and every
one of them is reported as `IMPLIED-UNRECORDED` with the drift invisible — an integrity report
that reads clean over 417 known-drifted keys. Whether a part-drifted pair should be its own class
or should count in DANGLING is a judgement, hence RUN rather than LOCAL.

---

## src/resync_roll.py

### F15 — the write verdict is discarded and the script then reports success  (LOCAL, MAJOR)

    82   if changed and not dry:
    85       silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)
    86
    87   verb = "Would fix" if dry else "Fixed"
    88   print(f"{verb} {len(changed)} roll entries out of sync with their record files:\n")

`silence.write_json` "Never raises on a denied replace: `replace_retry` records it and the caller's
write lands next round" (silence.py:363). So on a denied rename — the Windows reader-holds-target
case this project hits often enough to have written `replace_retry` for — `SWEEP_ROLL.json` is
unchanged and the operator is told "Fixed 27 roll entries", then reads a `roll now:` summary
computed from the in-memory copy that was never persisted. The two sibling artifacts written the
same way in this batch both gate on the verdict and say so at length: `worldseed.py:331-334`
("WRITE DENIED ... it lands on the next run") and `burgs.py:257-264` (prints to stderr and
returns 1). This one was missed.

---

# QUESTIONS

1. **`chain.py` has no plant-wide interlock.** `main()` (451) starts harvesting and issuing model
   calls with no `escalation.assert_clear`. `verify_math._INTERLOCKED` (4397) is an explicit list
   of eight jobs and `chain.py` is not on it, so this looks deliberate — chain normally runs
   inside `pipeline.phase_chain`, under pipeline's interlock. But `chain.py --limit N` is a
   directly runnable job that spends the pool and the card, and the library is HALTED. Should it
   join the list, or is running chain by hand during a halt intended? Same question, same shape,
   for `custodes.py`, `worldseed.py`, `burgs.py`, `thread_integrity.py` and `resync_roll.py`
   (the last one writes a shared artifact during a halt).

2. **`CHAIN.json`'s `unmatched` field is a top-40 truncation.** `write_result` stores
   `unmatched.most_common(40)` (chain.py:108). It is a diagnostic, not a work list, so Hard Rule 0
   may not bite — but it is a published artifact field that silently drops the tail, and the tail
   is the part a later pass would use to widen `entity_index`. Keep, or store whole?

3. **`CASCADE_TRIES = 5` under a comment that says three.** read.py:217-219: "Each attempt claims
   a different bucket, so three is three providers, not one provider three times." followed by
   `CASCADE_TRIES = 5`. Is 5 the intended value with a stale sentence above it, or the reverse? I
   could not tell which one is the erratum, so it is a question rather than F-anything.

4. **`worldseed.to_options` derives `tier` by stripping non-digits from the band**
   (`int(re.sub(r"\D", "", band) or 0)`, line 167). Every magnitude on disk today is `unassayed`
   or a bare `M0`-`M5` (sampled 60 record files: 16,863 `unassayed`, 49 banded, none with a
   decimal), so this is correct now. If a decimal Assay ever lands in `entry["magnitude"]`
   ("M3.52"), `tier` becomes 352 and every such world silently pins to the `states = min(40, ...)`
   ceiling. Worth a `band.split(".")[0]`, or is the clamp considered adequate?

5. **`burg_count` applies the condition factor a second time.** `largest_city` already scales P_1
   by condition (0.15 for ruined), then `burg_count` scales n by condition again (0.3 for ruined),
   so a ruined world is thinned twice while the docstring argues the count is "a consequence of
   the law rather than a second parameter that could disagree with it" (burgs.py:99-110). The
   comment at 115 acknowledges the second factor deliberately. Intended compounding, or one of
   the two?

6. **`thread_integrity.main` prints two classes that cannot occur.** `RECIPROCAL` (172-175) and
   `ASYMMETRIC-SUSPECT` (176-180) are unreachable while `recorded is None`, which `main` always
   passes. The module docstring says this is the Step-4 state, so it reads deliberate — flagging
   only so the next sweep does not re-file it as dead code.
