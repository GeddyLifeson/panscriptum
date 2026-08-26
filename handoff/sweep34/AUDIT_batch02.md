# SWEEP #34 — BATCH 02 AUDIT

Modules read end to end: `src/pipeline.py` (2,150), `src/sweep_plan.py` (332),
`src/tuning.py` (263), `src/descending_ladder.py` (216), `src/catalogue_models.py` (183).
3,144 lines.

Auditor only. Nothing under `src/` was edited. Every finding below is quoted from the source
as it stands at the time of reading (2026-08-25); `pipeline.py`, `descending_ladder.py` and
`catalogue_models.py` all took fixes earlier the same day and where a finding touches recent
work it says so.

Method note: findings are things I can prove by quotation, plus — where the claim is about the
world rather than the text — a reading of the data on disk. Everything that might be a
deliberate design decision is in QUESTIONS, not FINDINGS.

---

## src/pipeline.py

### F1 (MAJOR) — the unattended runner permanently stops working once the phase pointer walks past 8

`main()`:

```
2087    phases = [args.phase] if args.phase else list(range(st.get("phase", 1), len(PHASES) + 1))
2088    for ph in phases:
...
2097        try:
2098            fn(c, st)
...
2107        log(f"=== PHASE {ph} COMPLETE ===")
2108        st["phase"] = ph + 1
2109        save_state(st)
2110        update_handoff(st)
2111
2112    log("runner exiting")
```

Three things follow from those lines together.

1. `st["phase"] = ph + 1` executes **unconditionally** after `fn(c, st)` returns. Several
   phases return early precisely so their unit stays open for the next run —
   `phase_history` line 1697 ("Leaving phase 6 open rather than recording an empty result;
   the next run retries after phase 5 rewrites it"), `phase_shelve` lines 1805 and 1841,
   `phase_write`'s `landed.append(False)` at line 1976. The pointer moves past them anyway.
2. Nothing in `main()` ever reads `st["done"]`. `gate_done`'s docstring (line 508) promises
   "leaving the unit open so the next run redoes it", and `_landed` (line 483) promises "this
   unit stays open so the next run redoes it" — but for phases 3–8 the resume point is
   `st["phase"]`, not the done-keys, and no code path lowers it.
3. Once `st["phase"]` reaches 9, `range(9, 9)` is empty. The `for` body never executes, `main()`
   logs `runner exiting` and returns 0. `overnight.py:807` and `overnight.py:842` start
   `pipeline.py` with **no** `--phase` twice per cycle, so from that point every cycle is a
   silent no-op that reports success.

The module docstring at line 41 still advertises the opposite:

```
41      python3 src/pipeline.py            # run all implemented phases in order, forever
```

Corroboration from disk: `state/PIPELINE_STATE.json` holds `phase: 2` with
`done.write == ["all", "all", "all", "all", "all"]` — the ladder has been walked to the end
five times and the pointer has been put back by hand (`--phase N` writes `st["phase"] = ph`
at line 2094) five times. `health.py --reopen --go` (line 492) reopens stranded entrypass
batches by editing `st["done"]["entrypass"]` and does not touch `st["phase"]`, so a repair
made while the pointer sits past 2 reopens work the runner will never revisit.

### F2 (MAJOR) — the P8 meta-language ban is enforced by nothing

```
2119   # ------------------------------------------------------------------ P8: the meta-language ban
2122   # "these books should read like in-universe books only, nothing meta about the game they are
2123   # designed for" -- owner, on file. Ground Rule 4 says it, the model ignores it, so it is
2124   # enforced in code like scale_note and the Marginalia cap before it.
...
2142   def assert_in_universe(prose, where=""):
2143       """Raise on meta leakage. Callers in the write phase should reject and regenerate rather
2144       than publish -- a single 'as a DM you might' in a finished volume breaks the frame for
2145       every entry around it."""
```

`grep -rn "assert_in_universe" src/` returns exactly one hit — the definition. There are no
callers. `generate.py`, which is what actually turns a manifest into prose, does not import
`pipeline` at all (`grep -rn "import pipeline" src/` lists 35 modules; `generate.py` is not
among them). `meta_violations` is reached only from `audit.py:105`, which reports on
`scale_note` text after the fact.

So the comment's "it is enforced in code" describes behaviour the code does not have, and the
guard rail `phase_write`'s own docstring calls "this phase's own job" (line 1900) is not on the
path any prose travels.

### F3 (MAJOR) — four shared-file writers still use a fixed `path + ".tmp"`

```
187        tmp = STATE + ".tmp"                     # save_state
463        tmp = path + ".tmp"                      # write_record_catalogue
526        tmp = path + ".tmp"                      # land_json
591        tmp = path + ".tmp"                      # write_record
```

`silence.write_json`'s docstring names this exact shape as the hazard it was built to remove:

> THE TMP NAME CARRIES PID AND THREAD, which the older hand-rolled `path + ".tmp"` sites did
> not. Two writers of the same path otherwise collide on the temp file itself, and the loser
> can replace the winner's target with a partial file

and `pipeline.py`'s own run-#33 comment at 1489–1494 declares the problem closed:

```
1489   # this one called `os.replace` directly and simply lost the round to the `except` below. And
1490   # the temp NAME carried neither pid nor thread, so two writers of this file collide on the
1491   # temp itself and the loser can rename its own half-written copy over the winner's -- the
1492   # collision `silence.write_json` was built to make unavailable at twelve sites on 2026-08-25,
1493   # still open at this one. (run #33)
```

`update_handoff` was duly fixed (line 1495 builds a pid/tid temp). Its four siblings in the same
file were not. This matters most for `data/records/*.json`, which this file documents at length
as having **two sanctioned writers by design** (`write_record` / `write_record_catalogue`,
lines 597–612) — the one place in the tree where a temp-name collision is not hypothetical.
`threading` is already imported at line 52.

### F4 (MAJOR) — `gate_done` appends "all" on every run, and the live state file already shows it

```
487    def gate_done(st, phase, landed):
...
504        if all(landed):
505            st["done"].setdefault(phase, []).append("all")
506            return True
```

Nothing checks membership first. The same defect was found and fixed for entrypass ninety
lines earlier, with the reason written down:

```
1339            if landed and all(entry_settled(e) for e in batch):   # same predicate as the
1340                if key not in done_keys:      # a reopened grown batch is already recorded --
1341                    done_keys.append(key)     # re-appending would grow the resume list forever
```

Same unguarded append at `phase_chain:1555`, `phase_history:1699`, `phase_write:1926`.

On disk right now, `state/PIPELINE_STATE.json`:

```
weave      ["all", "all", "all", "all"]
cosmology  ["all", "all"]
history    ["all", "all", "all", "all"]
shelve     ["all", "all", "all", "all"]
write      ["all", "all", "all", "all", "all"]
```

And `drill.py` asserts exact equality against a one-element list:

```
986        return st["done"].get("cosmology") == ["all"]
994        return st["done"].get("write") == ["all"]
```

Those two nets pass only because they build a fresh `st = {"done": {}}` (lines 984, 992). Held
against the live file they are already false, and would be false forever.

### F5 (MINOR) — four stale `silence.note` line-number tags

```
406            silence.note("pipeline.py:191")          # call site is line 406
568        silence.note("pipeline.py:301")              # call site is line 568
717        silence.note("pipeline.py:261")              # call site is line 717
730         on_corrupt=lambda _p: silence.note("pipeline.py:277"))   # call site is line 730
```

Every other tag in the file is a name (`pipeline.py:vram`, `pipeline.py:write_record-merge`,
`pipeline.py:phase_shelve-spine`), which is why these four read as coordinates rather than as
labels. `pipeline.py:261` in particular now points into `_pool_answer_usable`, a function with
no handler in it. These are the ledger keys `health.py --failures` groups by, so a reader
chasing a wall of `silent:pipeline.py:261` records is sent to the wrong function.

### F6 (MINOR) — `_SCALE_EVIDENCE` is compiled and never used

```
1060   _SCALE_PATTERNS = [_MAGNITUDE.pattern, _ACT.pattern, _OBJECT.pattern]   # kept for reference
1061   _SCALE_EVIDENCE = re.compile("|".join(_SCALE_PATTERNS), re.I)
```

`grep -rn "_SCALE_EVIDENCE" src/` returns one hit: line 1061. `_SCALE_PATTERNS` returns two:
its definition and line 1061. Neither is imported anywhere. This is the OR-ed disjunction the
long comment above it (lines 996–1011) explains at length was **replaced** by conjunction —
"Hence conjunction rather than disjunction" — left compiled next to the gate that replaced it.
`valid_scale_note` uses `_MAGNITUDE`, `_act_upon_object`, `_PATIENT` and `_REPUTATION` and never
touches `_SCALE_EVIDENCE`. A future reader reaching for "the scale-evidence regex" would pick up
the one the corpus measurement discredited.

### F7 (MINOR) — two spellings of "how many buckets answer", one of which has no notion of staleness

`pipeline.py`:

```
243    def _pool_answering(ttl=120):
244        """How many cloud buckets actually answer, from the proof -- never from headroom."""
...
250                _PHASE_POOL["n"] = sum(1 for r in rows
251                                       if isinstance(r, dict) and r.get("verdict") == "answers")
```

`tuning.py`:

```
138    def _answering_buckets():
139        """How many cloud buckets actually ANSWER -- from the proof, not from reported headroom.
...
153        n = sum(1 for r in rows if isinstance(r, dict) and r.get("verdict") == "answers")
154        if age > PROOF_STALE_SECONDS:
155            # A stale proof is a claim about a pool that may no longer exist. Believe it, but say so.
156            return n, "%d answering (proof is %.1fh old)" % (n, age / 3600)
```

Same file, same predicate, two copies. `pipeline.py`'s copy never reads the proof's mtime, so it
believes an arbitrarily old `POOL_PROOF.json` with nothing to say about it, and caches for 120s
against tuning's 180s.

This is the defect `ask_pool_first` fixed **for the threshold** thirty lines below, in the
project's own words:

```
310        # THE THRESHOLD IS TUNING'S, NOT A SECOND COPY OF IT. This read `>= 3` as a bare literal
311        # while `tuning.CLOUD_MIN_BUCKETS` held the same 3 ... Two spellings of one policy: raise
312        # it there and this call site silently keeps the old bar.
```

The threshold was centralised; the measurement it is compared against was not.

---

## src/sweep_plan.py

### F8 (MAJOR) — seven data-reading handlers swallow without a note, in the module whose whole job is proving nothing was silently skipped

The project's own instrument says so. `python src/silence.py --all`:

```
SILENCE AUDIT — 612 exception handlers in src/
  SILENT (swallow and continue)       : 143
    16  drill.py
    14  mutate.py
    13  gpu_lane.py
    13  sweep_plan.py           lines 101, 201, 223, 247, 270, 173, 178, 163, 58, 111, 233, 280
```

Fourth worst module in the tree. Five of the thirteen (58, 111, 163, 233, 280) wrap
`import silence` itself and are unavoidable — the recorder cannot record its own absence. The
other seven read data and are not:

```
99         try:
100            paths = sorted(glob.glob(os.path.join(SHARDS, "*.json")))
101        except Exception:
102            return out                     # _read_shards -> {} -> "nothing has ever swept"

221        try:
222            paths = sorted(glob.glob(os.path.join(SHARDS, "*.json")))
223        except Exception:
224            paths = []                     # covered_by -> set() -> missing() names EVERY module

268        try:
269            paths = glob.glob(os.path.join(SHARDS, "*.json"))
270        except Exception:
271            paths = []                     # latest_run -> None
```

plus 173, 201, 247 and 318, each a `try: json.load(COVERAGE) ... except Exception: pass`.

The 223 case is the sharpest: `missing()` is the file's stated completeness proof — "the check
that proves nothing was dropped" (line 17) — and a swallowed glob error turns a fully-covered
sweep into a report that every module in `src/` was skipped, with nothing anywhere saying the
directory could not be listed. Line 173 has a second edge: `record()` reads the aggregate at 168
to fold old entries in, and if that read fails silently the shards-only `data` is written over
`SWEEP_COVERAGE.json` at line 177, dropping any pre-shard history.

This module is not a bystander here — it is the one that ends up in front of the owner as the
sweep's completeness statement, and `verify_math.py:4202` reads `missing(latest_run())` directly
as "the live sweep proves its own completeness".

### F9 (MINOR) — `coverage_map()` has no callers, and the CLI bypasses it

```
186    def coverage_map():
187        """The authoritative view: shards first, the aggregate file only where a shard is absent.
```

`grep -rn "coverage_map" src/` returns one hit outside the definition — line 209, a docstring in
`covered_by` mentioning it. No code calls it. Meanwhile the CLI path that would want "the
authoritative view" reads the non-authoritative file directly:

```
314        elif a.coverage:
315            try:
316                with open(COVERAGE, encoding="utf-8") as f:
317                    data = json.load(f)
318            except Exception:
319                data = {}
```

So `--coverage` — documented at line 20 as "what the last sweep actually covered" — reports
from the convenience view that `record()`'s own docstring says "nothing draws a conclusion from"
(line 139), while the function written to answer that exact question sits unused. Either the
CLI should call it or it should go; both are curatorial.

---

## src/tuning.py

### F10 (MINOR) — `MIN_CALLS_TO_JUDGE` has a second spelling, and the check that claims to pin them together compares a literal to a literal

`tuning.py`:

```
84     # Below this many recorded calls the rate is noise and is not allowed to veto. A handful of
85     # failures during a provider blip must not flip the whole library to local.
86     MIN_CALLS_TO_JUDGE = 20
```

`standards.py`:

```
58     MIN_CALLS_TO_JUDGE_RATE = 20    # below this a success PERCENTAGE is noise, not a measurement.
59                                     # Mirrors tuning.MIN_CALLS_TO_JUDGE (20), which already answers
60                                     # this exact question for regime().
```

`verify_math.py`, the check that exists to hold them together:

```
2967   check("the threshold itself is the one tuning.py already settled on",
2968         _STx.MIN_CALLS_TO_JUDGE_RATE, 20,
2969         note="tuning.MIN_CALLS_TO_JUDGE=20 answers this same question for regime()")
```

The check compares `standards.MIN_CALLS_TO_JUDGE_RATE` against the **literal** `20`. Raise
`tuning.MIN_CALLS_TO_JUDGE` to 30 and the check still passes, green, while the two policies have
diverged — which is precisely the failure its own `note` names. It is a check that cannot fail
at the thing it says it is checking. The one-token fix (`_TUNx.MIN_CALLS_TO_JUDGE` in place of
`20`) makes it real.

---

## src/descending_ladder.py

### F11 (MAJOR) — the whole module is unreached, and the gap its docstring says it fills is still open

`grep -rn "descending_ladder\|DESCENDING\|rung_for_length\|shrink_report\|transgression_bits\|rung_table\|FOLD_RUNG\|FOLD_GLYPH\|compton_confinement_energy\|density_at_scale\|schwarzschild_radius" src/ --include=*.py`, excluding the file itself, returns:

```
src/anchors.py:43:    "transgression": "bits of exception length (X.2 §4, Rissanen). Use transgression_bits()."
src/derivation.py:476:SCAN_MODULES = ["assay", "feats", "cosmography", "propagation", "descending_ladder", ...
src/secondopinion.py:23:   Found `descending_ladder.py:129 from_m` and two others at 100% confidence.
```

One prose pointer, one scan-target list, one historical note about a past finding. Nothing
imports the module; nothing calls any of its seven public functions.

The docstring states the problem it exists to solve:

```
14     Worse, the omission is silently load-bearing. X.2's Reach axis is measured in metres and its
15     band edges are "rung-characteristic lengths" -- but there are no rung-characteristic lengths
16     below 1e7 m, so every sub-planetary Reach is scored against a floor that does not exist.
18     THE FIX, IN ONE SENTENCE
20     The Ladder is extended downward by fifteen rungs to the Planck length
```

The Reach axis is still scored off a hand-written table in `assay.py` that has its own
sub-planetary edges and never consults this file:

```
assay.py:74     "M0":  dict(ruin=1e2,   reach=1e0,   celerity=1e0, ...
assay.py:75     "M1":  dict(ruin=1e7,   reach=1e2,   ...
```

The fifteen rungs, the Fold, the confinement energetics and `transgression_bits` are all
correct as written (I checked the table's monotonicity in length, the `rung_for_length` domain
guards at both ends, and `PLANCK_ENERGY = 1.956e9 J` against `m_P c²` = 1.9561e9 J). The defect
is not in the arithmetic. It is that a module written to close a named gap was never connected
to the thing with the gap, so the gap is still there and the file reads as though it were not —
which is the same shape as `phase_chain`'s own docstring (`pipeline.py:1538`): *"A finished stage
that nothing dispatches to is indistinguishable from a stage that was never written."*

`anchors.py:43` compounds it by telling a reader to "Use `transgression_bits()`" for the
transgression anchor, which no code does.

### F12 (MINOR) — G is the one constant in the file that is not in the constants block, and five constants are re-spelled in `scale_theories.py`

```
39     # ---------------------------------------------------------------- real constants (SI, cited)
40     PLANCK_LENGTH = 1.616255e-35   # m   (CODATA)
...
45     HBAR = 1.054571817e-34         # J*s
46     BOLTZMANN = 1.380649e-23       # J/K
```

then, 95 lines later:

```
141        return (2.0 * 6.67430e-11 * mass_kg) / (C_LIGHT ** 2)
```

`scale_theories.py` spells the same physics a second time and does name it:

```
scale_theories.py:23   C_LIGHT = 2.99792458e8
scale_theories.py:24   G_NEWTON = 6.67430e-11
scale_theories.py:25   HBAR = 1.054571817e-34
scale_theories.py:26   NUCLEAR_DENSITY = 2.3e17
scale_theories.py:27   PLANCK_LENGTH = 1.616255e-35
```

Five constants, two files, and `NUCLEAR_DENSITY` in particular is a *judgement* (saturation
density of nuclear matter, used as the transgression pivot at `descending_ladder.py:209`) rather
than a CODATA lookup, so the two copies can drift on purpose in one place and by accident in the
other. `BOLTZMANN` at line 46 is also unused in this file and re-spelled again as `K_BOLTZMANN`
at `chord_field.py:38`.

---

## src/catalogue_models.py

### F13 (MAJOR) — a provider that could not be probed contributes nothing to `stale`, so "0 stale in the cloud pool" is measured only over the providers that answered

```
133        for name in sorted(provs):
134            r = live.get(name)
135            asks = [a for a in (want.get(name) or []) if a]
136            if not r:
137                why = next((x.get("error") for x in rows if x["provider"] == name), "?")
138                print(f"  {name:<16}-- {why}")
139                continue
```

The `continue` prints the error to the console and drops the provider. Nothing about it reaches
`stale`, and `stale` is the only field the standard consumes:

```
standards.py:1396        _stale_rows = pm.get("stale") or []
standards.py:1397        _local = [r for r in _stale_rows if (r.get("provider") or "") == "ollama"]
standards.py:1398        _cloud = [r for r in _stale_rows if (r.get("provider") or "") != "ollama"]
standards.py:1399        stale = len(_cloud)
...
standards.py:1440            "0 stale in the cloud pool, catalogue under %dh old" % MAX_PROVIDER_MODELS_AGE_H,
```

Read from `data/PROVIDER_MODELS.json` as it stands (stamped 2026-08-25 20:21): 26 providers,
of which **13 never produced a model list** — 10 `no key`, plus one 405, one 410 Gone, one 401,
one 402 Payment Required. Half the pool is unmeasured, and the standard's headline number is
computed as though it were measured and clean.

The module's own opening argument is exactly this failure:

```
20     **The keys work. The model NAMES are stale.** Providers retire and rename models constantly,
21     and a config written months ago points at a graveyard -- so capacity that is paid for,
22     authorised and live reads as a dead provider.
```

A provider whose probe 410s is precisely a provider whose configured model name cannot be
checked, and it is now recorded in a shape that reads identically to a provider with nothing
stale. The `providers` rows on disk *do* carry the errors, so the information exists; it simply
never reaches the field the standard reads. An `unmeasured` list in the payload, and the
standard refusing to call itself green while it is non-empty, is the shape this wants.

### F14 (MINOR) — a 200 response carrying an empty model list is reported as "no model list endpoint"

```
101            if ids:
102                return {"provider": name, "url": url, "models": sorted(ids)}
103        except Exception as e:
104            silence.note("catalogue_models.py:ask_provider")
105            last = f"{type(e).__name__}: {str(e)[:70]}"
106    return {"provider": name, "error": locals().get("last", "no model list endpoint")}
```

If a provider answers 200 with `{"data": []}` — or with rows that carry neither `id` nor
`name` — no exception is raised, `last` is never bound, and the caller is told the provider has
no listing endpoint. That is a different fault with a different remedy (the endpoint is fine;
the account serves nothing), and `silence.note` is not called on that path either, so it leaves
no ledger record. Latent as of today's snapshot — no row carries that error string — but it is
the plausible-negative shape the tree is being swept for.

---

## QUESTIONS — not filed as orders

1. **`pipeline.py:801`, `fl[:3]`** — `synthesis_prompt` shows at most three mined feats per
   entity. `synthesis_blocks` (line 760) ranks entities by feat count and, per the 2026-08-25
   owner ruling at lines 763–789, no longer truncates the entity list; but the *evidence* per
   entity is still capped at three, ranked by whatever order the feats file happens to hold.
   Is that a prompt-size budget like the `[:300]` on descriptions (clearly fine), or the same
   ranked-truncation the ruling removed one level up? I could not tell which, so I did not file
   it.

2. **`pipeline.py:1099-1105`, `valid_scale_note`'s docstring** — "Three gates, in order of
   severity: 1. too short 2. STAT-BLOCK 3. no scale evidence at all". The body has six branches;
   the two the surrounding comments argue hardest for (`_PATIENT`, `_REPUTATION`) are not among
   the three named. Is "no scale evidence at all" meant to cover the last four collectively, or
   has the docstring fallen behind? Cheap to fix either way, but I will not file a docstring
   order on a reading I am not sure of.

3. **`pipeline.py:1612`** — `records = {r["source"]: r for r in WI.load_records()}` shadows the
   module-level `records()` function inside `phase_cosmology`. Harmless today (the function is
   not called again in that scope). Rename, or leave it?

4. **`pipeline.py:1629`, `kinds.most_common(6)`** — six is exactly the number of grounding kinds
   that exist (`grounding.GROUNDINGS` has five, plus `UNGROUNDED`), so today this truncates
   nothing. It becomes a silent truncation the moment a sixth grounding is added. Deliberate
   tightness, or a cap waiting to happen?

5. **`tuning.py:96 / 220`** — `PROFILES["cloud"]["workers"] = 12` is never used: `profile()`
   overwrites it for the cloud regime at line 220 with `max(4, min(16, n + 2))`. The comment at
   93–95 explains that derivation, so the 12 may be intentional documentation of a former
   default. Is it worth removing, or does it earn its place as the shape of the dict?

6. **`tuning.py:218-220`** — `regime()` caches its verdict for `RECHECK_SECONDS` (180s) but
   `profile()` re-reads `_answering_buckets()` live on every call. So the regime label and the
   worker count sizing it can come from two different reads of `POOL_PROOF.json`; a cached
   "cloud" paired with a freshly-emptied pool yields `workers = 4` under a cloud profile. Not
   incorrect, but the two halves of one decision are asynchronous. Intended?

7. **`catalogue_models.py:91`** — `"Authorization": f"Bearer {key}" if key else ""` sends an
   empty `Authorization` header for local providers rather than omitting it. Some servers reject
   an empty header outright. Deliberate simplification?

8. **Out of my batch but seen in passing** — `health.py:489` prints `for k in reopen[:20]`, a
   cap on a roster of stranded batches, on the line a person reads to decide whether to run
   `--go`. Same shape as the `refused[:5]` cap that `pipeline.py:1949` removed in run #33. I did
   not file it because `health.py` belongs to another batch; flagging it so it is not missed.
