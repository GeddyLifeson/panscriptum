# Sweep #28 — Batch 07 Audit

Modules: `src/magnitude.py` (1045 lines), `src/completeness.py` (455), `src/address_space.py`
(346), `src/feats_index.py` (263), `src/propagation.py` (214), `src/cosmology_graph.py` (159).
Total 2482 lines, every line read.

Read `NEXT_STEPS.md` §3 first per instructions; the "ALREADY KNOWN" items for this batch's
modules are marked KNOWN below with a re-verification note. Everything else is NEW.

---

## SPECIAL FOCUS (a): `completeness.host_reachable()` and the dandwiki RAW-mode failure

**Confirmed exact mechanism.** `completeness.py:193-208`:

```python
try:
    import endpoint as EP
    base = EP.api_url(host)
    if not base:
        _REACH[host] = False
        return False
    _REACH[host] = bool(EP._get(base + "?action=query&meta=siteinfo&format=json", timeout=timeout))
except Exception:
    silence.note("completeness.py:host-unreachable")
    _REACH[host] = False
return _REACH[host]
```

`endpoint.api_url(host)` (`endpoint.py:176-179`):

```python
def api_url(host):
    """The API base for this host, or None when it has no usable API."""
    d = detect(host)
    return f"https://{host}{d['path']}" if d["mode"] == MODE_API else None
```

`detect()` classifies every host into exactly one of `MODE_API`, `MODE_RAW`, `MODE_DEAD`
(`endpoint.py:126-173`). `api_url()` returns `None` for **both** `MODE_RAW` and `MODE_DEAD` —
it only ever returns a URL for `MODE_API`. `dandwiki.com` is a confirmed `MODE_RAW` host
(`endpoint.py:11-26`'s own header names it as the motivating case: its `/api.php` answers every
request with HTTP 403, and it is read via `action=raw` instead). So for dandwiki,
`EP.api_url("www.dandwiki.com")` always returns `None`, `host_reachable()` takes the `if not
base:` branch unconditionally, sets `_REACH[host] = False`, and returns `False` — **regardless
of whether the host is actually up**. `endpoint.py` already has the right primitive for this
host (`raw_url(host, title)` / `fetch_raw`), but `host_reachable()` never calls it; it only ever
tries the API path.

**Minimal correct fix:** branch on `EP.detect(host)["mode"]` instead of assuming API-only:
- `MODE_API` → current behaviour (probe `api_url(host) + "?action=query&meta=siteinfo..."`).
- `MODE_RAW` → probe via `EP.raw_url(host, "Main Page")` (or any known-good raw title) through
  `EP._get(...)`, treating a non-error-page response as reachable — the same logic `detect()`
  itself already uses to classify a host as `MODE_RAW` in the first place (`endpoint.py:154-164`:
  a raw view returns wikitext, an error page returns HTML starting `<!doctype`/`<html`).
- `MODE_DEAD` → unreachable, as today.

This is **KNOWN** (`NEXT_STEPS.md` §3, "completeness.py:194-268") and confirmed **STILL OPEN** —
the code is unchanged from the description; the above pins the exact branch and the exact
one-line fix.

---

## SPECIAL FOCUS (b): `magnitude.py --calibrate` and the 34h-stale "reproduces the charter" standard

**Confirmed: `calibrate()` has ZERO checkpointing, unlike its sibling `run_batch()`.**

`calibrate()` (`magnitude.py:782-838`) loops over all 6 `BENCHMARKS` **sequentially**
(`magnitude.py:800: for name, host, band, val, ci, epoch in BENCHMARKS:`), calling
`assay_entity()` for each — which does live wiki evidence mining (`F.evidence_for`), then a
pool/local-model call that on the local-only path carries a **420-second timeout**
(`assay_entity`'s `P.ask(..., timeout=420, ...)`), and for any benchmark whose evidence exceeds
`ONE_SHOT_MAX` (30000 chars) — plausible for the heavier benchmarks (Goku, Naruto) — falls
through to `_split_assay()`, which issues **up to 11 axis calls plus 1 anchor call**, each
axis potentially multiple `SPLIT_SLICE`-sized (8000-char) sequential sub-calls. The **only**
durable write in the whole function is at the very end, after the loop over all 6 benchmarks
completes:

```python
out = {"at": time.time(), "model": c["model"], "results": rows}
_cr = os.path.join(HERE, "data", "CHARTER_REGRESSION.json")
with open(_cr + ".tmp", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
silence.replace_retry(_cr + ".tmp", _cr)
```

(`magnitude.py:829-836`.) There is no per-benchmark write of the kind `run_batch()` does — its
own docstring says explicitly (`magnitude.py:930-935`): *"Written to be killed... ASSAYS.json
is rewritten on each completion and `--resume` skips anything already in it."* `calibrate()` has
no such property and no docstring claim of one; it is a single 6-entity batch job with a single
end-of-run write.

This is exactly the mechanism run #27 traced (NEXT_STEPS §"lessons" item 6 / OWNER RULING #6):
`foreman` re-dispatches `magnitude.py --calibrate` roughly hourly and `kill_stalled_job` kills
each attempt before it reaches its one and only durable write, so `CHARTER_REGRESSION.json`
never gets rewritten no matter how many times the job runs — it is being killed, not stalled.

**Minimal correct fix:** checkpoint incrementally, mirroring `run_batch()`'s own pattern —
write (or append-and-atomically-replace) `CHARTER_REGRESSION.json` after **each** benchmark's
`rows.append(row)` inside the `for` loop, not once after all 6. A kill mid-run then loses at
most the one benchmark in flight, and the standard reading the file sees a growing, aging
partial result instead of a permanently stale one.

This is **KNOWN** (`NEXT_STEPS.md` §"lessons" item 6 / owner ruling #6, batch 15's trace) and
confirmed **STILL OPEN** — the code is unchanged; the above pins the exact write-count (1 write
per full run, at the very end) that makes the kill-mid-run failure total rather than partial.

---

## magnitude.py

1. **[HIGH, KNOWN]** See Special Focus (b) above — `calibrate()` (`:782-838`) has no
   checkpointing; its single write is at `:829-836`, after all 6 sequential benchmarks finish.

2. **[MED, KNOWN]** `:335-351` `verify()` — the retry-on-all-verbatim-failure gate at `:688`
   (`if not sheet and any(cand.values()):`) does not fire when status axes coexist with failed
   numeric axes, because `verify()` sets `sheet[ax] = cited or st` for every STATUS axis
   (`"none"`/`"unestimable"`/`"n/a"`) unconditionally (`:350`), regardless of whether any
   numeric citation validated. The system prompt itself tells the model "Most entities have
   evidence for two or three axes... Returning nine statuses and two scores is a correct
   answer" — i.e. the common, expected shape is exactly the one that defeats this guard: a
   sheet with a few numeric axes (all citation-invalid) and several honest status axes makes
   `sheet` non-empty, so the quality-failure retry at `:688-712` never triggers, and a
   one-shot answer whose every numeric citation was fabricated/paraphrased is filed as a
   legitimate (if partial) result instead of being retried via the split path. Re-verified live
   against current source, unchanged from NEXT_STEPS's description (there recorded at the old
   line numbers `:668-677`).

3. **[MED, KNOWN]** `:479-493` `_split_assay._one_axis()` — the inner per-slice loop:
   ```python
   got = _ask(c, SYSTEM, prompt, AXIS_SCHEMA)
   if not got:
       continue
   ```
   A transport failure on any individual `SPLIT_SLICE` (8000-char) sub-call is silently
   skipped with no `silence.note` and no record in the returned worksheet — indistinguishable
   downstream from "none of this slice's sentences bore on the axis." For a heavyweight entity
   whose axis evidence spans several slices, a mid-run transport blip on one slice quietly
   removes that slice's evidence from consideration rather than being retried or flagged.
   Re-verified live, unchanged (NEXT_STEPS recorded this at old line numbers `:451-482`).

4. **[MED, KNOWN]** `:930-1004` `run_batch()`'s per-completion write of `data/ASSAYS.json`
   (`:985-996`) uses a hand-rolled fixed-name `OUT + ".tmp"` plus a manual 5-attempt
   `PermissionError` retry loop, instead of `silence.write_json`/`silence.replace_retry`. The
   write is correctly serialized against the **other threads of the same process** by
   `threading.Lock` (`:936`), so this is not an intra-process race. But the temp filename is
   **fixed**, not PID/thread-qualified the way `silence.write_json` deliberately is
   (`silence.py:262-266`: *"Two writers of the same path otherwise collide on the temp file
   itself, and the loser can replace the winner's target with a partial file"*) — so if a
   second `magnitude.py --batch` process is ever running concurrently against the same
   `ASSAYS.json` (plausible: NEXT_STEPS §6 already confirms `foreman` re-dispatches
   `--calibrate` on an overlapping cadence; the same re-dispatch risk applies to `--batch`),
   the two processes' `ASSAYS.json.tmp` writes can interleave and either process's
   `os.replace` can land a partial/mixed file. Re-verified live, unchanged (NEXT_STEPS recorded
   this at old line numbers `:966-983`).

5. **[LOW, NEW]** `main()`'s `--one` debug path (`ap.add_argument("--one", ...)` handling)
   prints `json.dumps(r, indent=1, ensure_ascii=False)[:4000]` — truncates the printed
   worksheet/rejection detail at 4000 characters when manually inspecting a single entity via
   `python magnitude.py --one HOST ENTITY`. Low impact: it is a manual CLI debug view, not
   persisted data, but it is exactly the shape Hard Rule 0 warns about (a cap on a diagnostic
   view) and would hide rejection detail for any entity with a large worksheet.

6. **[LOW, NEW — dead code, self-acknowledged]** `compose()` (`:524-556`) implements a
   round-robin evidence-budget/truncation branch (`if budget:` at `:531`) that is **never
   exercised**: `compose()` is called exactly once in the file, always with `budget=None`
   (`:610`). The author is aware — the returned `evidence_dropped_to_fit` field is commented
   `# always 0 now; kept so a future budget cannot be silent` (`:744-746`) — so this is
   flagged only as an unreachable-branch note per the lens, not a live bug.

---

## completeness.py

1. **[HIGH, KNOWN]** See Special Focus (a) above — `host_reachable()` (`:155-208`) gates on
   API-mode-only `endpoint.api_url()`; RAW-mode wikis (dandwiki confirmed) always read
   unreachable. Exact fix given above.

2. **[MED, KNOWN]** `:66-119` `category_size_probe()`'s 12h disk cache (`state/category_sizes.json`)
   is written from `audit()`'s `ThreadPoolExecutor(max_workers=workers)` (default 6,
   `:211,333`), via a **fixed-name** `_CS_CACHE_P + ".tmp"` (`:113`) written with `open(tmp, "w")`
   + `json.dump` + `silence.replace_retry` — not `silence.write_json`. Two mechanisms compound:
   - **RMW race with no lock at all:** `_cs_load()` returns the same shared module-global dict
     `_CS_CACHE["d"]` to every thread once loaded (`:71-79`); every worker thread that completes
     a probe does `cache = _cs_load(); cache[k] = {...}` (`:110-111`) on that **same mutable
     dict object**, then immediately `json.dump(cache, f)` (`:114-115`) while other threads may
     still be mutating it. Confirmed by direct reasoning about CPython's `dict` iteration
     contract: `json.dump` iterates `cache.items()` internally, and a concurrent `cache[k] = v`
     insertion of a **new** key from another thread during that iteration raises
     `RuntimeError: dictionary changed size during iteration` — which the surrounding
     `except Exception: silence.note("completeness.py:cs-cache")` (`:117-118`) swallows
     silently, so the write is simply dropped for that thread with no visible symptom beyond a
     `silence.note` entry.
   - **Fixed temp filename** means two threads (or, worse, two concurrent `completeness.py`
     processes) writing at the same moment can interleave content into the same `.tmp` path
     before either `os.replace` runs, risking a corrupted on-disk cache. `_cs_load()`'s own
     read path treats a corrupt/unparseable cache file as "no cache yet" and silently resets to
     `{}` (`:73-78`) — which defeats the cache's stated purpose (avoiding "~1,300 live calls
     per half hour to the domain that has IP-banned this machine once already", `:124-128`) and
     reopens exactly the IP-ban risk the cache exists to prevent.
   Re-verified live, unchanged (NEXT_STEPS recorded this at `:110-118`).

3. **[not a finding — verified as documented, intentional]** `audit().work()`'s
   `if not sizes and failed == 0: return None` (`:295-296`) silently drops a source from
   `COMPLETENESS.json` when every probe answered cleanly but none of the candidate category
   names matched. This is explicitly reasoned in the adjacent comment block (`:278-294`) as
   the deliberate complement to the `unreliable` bucket (genuine absence vs. transport
   failure) and is not new nor contradicted by the code — noting it only because it was worth
   checking against the lens, not because it is a bug.

---

## address_space.py

1. **[MED, KNOWN]** `:251-252` `assign().fit()`:
   ```python
   def fit(v, field):
       return (0 if v is None else int(v)) % (1 << WIDTHS[field])
   ```
   silently modulo-wraps any hyperverse/xenoverse/metaverse/multiverse tier index that is out
   of range for its field width, in direct contrast to `pack()` (`:145-159`), which **raises**
   `ValueError` on the identical out-of-range condition for every other caller. Two tier indices
   that differ by a multiple of the field's modulus (e.g. `WIDTHS["hyperverse"]` bits) silently
   alias onto the same shelfmark position — an ambiguous shelfmark presented as an unambiguous
   one. Re-verified live, unchanged (NEXT_STEPS recorded this at `:106-142,251-252`).

2. **[MED, NEW]** `shelfmark()`'s own docstring (`:171-177`) directly contradicts its own code:
   > *"H and X print as '?' because they are uncharted... This renders them the same way rather
   > than inventing positions nobody has surveyed."*

   but the function body (`:178-183`) prints real integers unconditionally:
   ```python
   return (f"Ω › H{f['hyperverse']} › X{f['xenoverse']} › Mt.{f['metaverse']} › "
           f"Mv.{f['multiverse']} › U-{f['universe']} › G.{f['galaxy']:x} › P.{f['planet']}")
   ```
   Verified live:
   ```
   >>> shelfmark(pack(hyperverse=1, xenoverse=1, metaverse=1, multiverse=1, ...))
   'Ω › H1 › X1 › Mt.1 › Mv.1 › U-0 › G.0 › P.0'
   ```
   no `?` anywhere. This is stale documentation left over from before `tiers.py` "charted"
   hyperverse/xenoverse — the module's own top-of-file docstring (`:75-105`) correctly
   describes the *current*, newer behaviour ("CHARTED 2026-08-20... The question marks come
   out"), but `shelfmark()`'s local docstring was never updated to match and still describes
   the pre-charting behaviour as current fact. The same root cause produces a second, adjacent
   contradiction: the comment immediately above `FIELDS` (`:127-129`) states *"hyperverse and
   xenoverse are NOT fields... reserving bits for them would invite filling them in"*, while
   the `FIELDS` list two lines below it (`:130-139`) defines both as fields with real bit
   widths (`:131-132`), which the earlier top-of-file docstring confirms is the intended,
   correct, current behaviour. Anyone reading only the local comments (not the whole module
   docstring) would draw the wrong conclusion about what the code does.

3. **[LOW, NEW]** Top-of-file docstring's `"74 bits, 10 bytes"` (`:27`) is stale versus the
   current, live-computed total: `address_space.TOTAL_BITS == 89` (≈11.1 bytes), confirmed by
   direct import — a leftover from the same pre-charting version referenced in finding 2.

---

## feats_index.py

No correctness, swallowed-failure, cap, or two-writer findings. The module is read-only (no
writes to shared state), `most_common()`/`Counter.most_common()` calls are uncapped
(`:256`, no `n` argument), `feats_for_source()` is explicitly documented and coded as
never-truncated (`:179-180`), and `_norm()`'s own docstring is a rare example of a
**self-corrected** comment (dated 2026-08-24, `:96-109`) that accurately states what the
function does and does not do, measured against real data (79/1241 records, 76 folding
correctly, 3 genuine catalogue gaps named). Nothing to flag.

---

## propagation.py

No correctness bugs found. `shortest()` (Dijkstra with early exit), `hops()`,
`ascension_years()`, `arrival_years()`, `observed_mark()` were traced by hand and spot-checked
live against `data/SHARED_STAGE_GRAPH.json` (172 shelves; sample probes all resolve to the
hops/distance the module's own demo table expects). No writes, no caps (module is read-only;
the CLI's hardcoded 6-pair `probes` list and 3-year `(100, 500, 1500)` sample points are
demonstration data for `main()`'s human-readable report, not a truncation of a real dataset).

1. **[LOW, NEW]** `:53` names a constant `BASE_YEARS_PER_HOP` in a comment describing what
   controls "how long news takes to cross one intermediary shelf" — no such constant exists
   anywhere in the codebase (confirmed by grep across `src/`); the actual, correctly-used
   constant is `YEARS_PER_UNIT_DISTANCE` (`:65`). Pure comment staleness, no functional impact.

---

## cosmology_graph.py

1. **[HIGH, NEW]** `main()`'s `--write` path (`:143-154`) applies an undisclosed hard cutoff
   when serialising the computed graph to `data/SHARED_STAGE_GRAPH.json`:
   ```python
   "pairs": [{"a": a, "b": b, "weight": round(w, 3), "shared_sample": pair_shared[(a, b)]}
             for (a, b), w in sorted(pair_w.items(), key=lambda kv: -kv[1])
             if w >= 1.0],
   ```
   (`:151`.) Measured live against the current `data/WEAVE_CANDIDATES.json`:
   ```
   total pairs (build_graph(), unfiltered): 3753
   pairs with w >= 1.0 (what actually gets written): 1087   (29%)
   pairs silently dropped: 2666   (71%)
   ```
   No field in the written JSON records that 71% of computed edges were discarded, or how many,
   or why. **Concrete downstream consequence, also measured live:** of the 197 distinct sources
   that share at least one real, mined co-attested entity with some other source (i.e. have
   genuine shared-stage evidence per `build_graph()`), **25 end up with zero surviving edges**
   and are **entirely absent** from `SHARED_STAGE_GRAPH.json` — not weakly connected, not
   flagged, simply not present as a key:
   ```
   2112 (Rush), DMs Guild: Heroes of Hell, DMs Guild: The Great Dale, Darksiders, Date A Live,
   Descent into Avernus, Extra Life, Ghosts of Saltmarsh, KBP Unlikely Heroes,
   Kenichi the Mightiest Disciple, Kinnikuman, Mage Hand Press, Pantheon: Korean,
   Pantheon: Polynesian, Problem Solverz, Rainbow Six, Rosario + Vampire, Sakamoto Days,
   The Amethyst / Cockroach King screenplay (Chroma Wastes), Warhammer Fantasy,
   Xanathar's Guide to Everything, the Lovecraftian mythos, the Skate games,
   the Solomonic tradition (Goetia, the Keys, the Shem angels), the Weaveshaper Ateliers
   ```
   `propagation.py`, which the module's own comment at `:144-145` names as a live consumer of
   this exact file ("propagation.py and resonance.py both read SHARED_STAGE_GRAPH.json live"),
   treats absence from the graph as full disconnection: `propagation.shortest()` returns
   `(math.inf, [])` for any `src`/`dst` not in `adj`, and `main()`'s own CLI prints
   `"?? not in graph: <name>"` (`propagation.py:209-210`) — indistinguishable from a source
   that genuinely shares nothing with anything, which is false for all 25 of the above. This is
   exactly the failure mode Hard Rule 0 exists to catch: *"a cap does not fail, it returns a
   smaller universe wearing the same shape as the real one."* It is also, by the module's own
   logic, backwards on the merits: the weighting formula `w = 1.0 / math.log(n + 1.5)` means
   even the **single strongest possible signal** — one rare entity co-attested by exactly the
   minimum `n=2` sources — scores only `1/log(3.5) ≈ 0.80`, already below the `1.0` write
   threshold on its own; a pair needs **at least two** such maximally-rare co-attestations to
   survive into the graph at all. That directly undercuts the module's own stated thesis
   (`:37-41`): *"a shared 'Zhentarim' is strong... rare shared entities bind, ubiquitous ones
   barely count"* — under the current threshold, one rare shared entity does *not* reliably
   bind two shelves in the persisted graph.

   Note the printed report (`main()`'s console output, `:127-141`) is unaffected — it computes
   `components()` and the "STRONGEST SHARED STAGES" table off the full, unfiltered in-memory
   `pair_w`, so a human running the tool interactively sees more connectivity than
   `propagation.py`/`resonance.py` ever will from the file it writes.

   **Not previously recorded** — grepped `NEXT_STEPS.md` and `HANDOFF.md` for `cosmology_graph`,
   `SHARED_STAGE`, and the literal filter text; the only prior finding on this file (m144, now
   fixed) was the unrelated `pair_shared[:8]` cap on the co-attested-entity sample list
   (`:86-93`), which the file's own comment confirms was corrected and is uncapped today.

---

## Coverage

6 modules, 2482 lines, every line read (verified via `wc -l` before and cross-checked against
each file's actual final line number while reading).

batch07: 6 modules, 2482 lines read, 3 high, 6 med, 4 low, report at handoff/sweep28/AUDIT_batch07.md
