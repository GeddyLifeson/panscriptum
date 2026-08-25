# SWEEP 31 — BATCH 02 AUDIT

Modules: `src/pipeline.py` (1975 lines), `src/weave_index.py` (276 lines), `src/runguard.py`
(219 lines), `src/catalogue_models.py` (176 lines), `src/module_index.py` (83 lines).
Total lines read: **2,729** (every line of all five files, read in full via `cat -n`).

Repo audited (read-only, no edits made): `C:\Users\imarl\panscriptum-library-kit`.

Findings are numbered and grouped by module. Severity: blocking / major / minor / cosmetic.
Confidence: VERIFIED (traced in source, failing input named) or HYPOTHESIS (plausible, not
provably triggered from these five files alone).

---

## src/pipeline.py

### F1. Chain phase silently discards harvested evidence below a hard-coded threshold, then permanently advances past it — VERIFIED, major/blocking

`phase_chain`, lines 1405–1433:

```python
rows = CH.harvest()
log(f"phase 4 chain: {len(rows):,} sentences read like a contest outcome")
if len(rows) < 10:
    log("  too few contests on record to fit anything; leaving the graph empty")
    st["done"].setdefault("chain", []).append("all")
    st["units_done"] += 1
    save_state(st)
    return
edges, unmatched, prov = CH.extract(rows, workers=c.get("workers", 8))
edges = CH.adjudicate_mutuals(edges, prov)
...
CH.write_result(edges, res, unmatched)   # one schema, one writer -- see chain.write_result
```

`CH.harvest()` has already done real work by the time this check runs — it found `rows` sentences
that read like contest outcomes. If `len(rows) < 10`, the function returns **without ever calling
`CH.extract` or `CH.write_result`** — the harvested rows are not persisted anywhere. Compare the
`res.get("error")` branch a few lines later (1420–1424): when the Bradley-Terry fit itself fails
(e.g. the graph isn't strongly connected), the code still calls `CH.write_result(edges, res,
unmatched)` and the comment explicitly defends this: *"Refusing is the correct answer, and it is
a RESULT -- the edges are kept and the graph is the finding."* The `<10` branch does not follow
its own file's stated policy: it keeps nothing.

Worse, `main()` (1912–1935) drives phase progression purely off `st["phase"]`, incrementing it
unconditionally once `fn(c, st)` returns without raising (line 1933: `st["phase"] = ph + 1`).
`st["done"]["chain"]` is written but **nothing in `main()` ever reads it** to decide whether to
revisit phase 4 — confirmed by `grep -n "done\[.chain.\]\|'chain'\|\"chain\""` returning only the
two write sites (1410, 1430) and the `PHASES` list itself. So on a corpus with, say, 8 real
contest sentences, phase 4 runs once, throws them away, marks itself permanently done, and moves
to phase 5 — and on every subsequent invocation of `pipeline.py`, `phases = list(range(st.get(
"phase", 1), len(PHASES) + 1))` starts at phase 5 or later, so phase 4 is never automatically
revisited even as the corpus grows to hundreds of contest sentences. Only an operator manually
running `--phase 4` again recovers it.

This is the same shape of bug the file elsewhere calls "Hard-Rule-0-shaped" (see the `with_feats`
comment at line 760) — a threshold gate that makes real, already-collected evidence disappear
rather than persisting a smaller-but-honest result.

**Failure scenario**: a young or thin corpus reaches phase 4 with 6 harvested contest sentences.
`CH.write_result` is never called; no chain-of-defeats output file is written for this run.
`st["phase"]` advances to 5 and stays there. Every later invocation resumes at phase 5+; the six
real contests are never assayed, never written, and the gap is invisible (nothing logs "chain
still pending" — the phase reads as cleanly completed).

### F2. Docstring claims an unbounded loop that main() does not implement — minor, VERIFIED (contradiction), tightly related to F1

Line 41: `python3 src/pipeline.py            # run all implemented phases in order, forever`.
`main()` (1887–1937) computes `phases = list(range(st.get("phase", 1), len(PHASES) + 1))`, runs
each once, and on reaching an unimplemented phase or exhausting the list, logs `"runner exiting"`
(1937) and returns — there is no re-poll / wait-and-retry loop anywhere in this file. In isolation
this reads as "processes everything currently available, once, however long that takes" rather
than a literal forever-loop; taken together with F1 it means a phase that made a permanently-wrong
decision (advanced past chain with real evidence unwritten) is never revisited by design, which is
the opposite of what "forever" suggests to a reader trying to understand resumability.

### F3. Hard Rule 0 cap: description-only ceiling-nomination fallback samples only 14 entries — major, VERIFIED

`phase_synthesis`, line 765:

```python
chunks = [with_feats[i:i + 14] for i in range(0, len(with_feats), 14)] or [rest[:14]]
```

The comment directly above (756–764) states the intent: *"EVERY feat-bearing entry is nominated
... no feat-bearing entry is ever excluded from nomination"* — true for `with_feats`, which is
fully chunked. But when a source has **zero** entries with mined feats, the fallback is
`rest[:14]`: only the top 14 entries by description length (out of however many the source has)
are ever shown to the model as ceiling candidates. This is exactly the bug class the same comment
says was fixed at BUGS m13 ("The fixed sample-of-14 could silently clamp a whole source to a
lesser ceiling whenever the true strongest entity ranked fifteenth") — fixed for the feat-bearing
path, left in place for the description-only path. The in-code defense ("a lead paragraph cannot
carry a ceiling feat") is a judgment call, not a proof; a source with a strong feat mentioned in
entry #40's description (shorter than 14 unrelated entries' descriptions, none of which have mined
feats either) never gets that entry considered.

**Failure scenario**: a 200-entry source with no mined feats anywhere and the actual power-ceiling
feat sitting in entry #97's description (a description shorter than the 14 longest, unrelated,
non-feat descriptions) never has entry #97 shown to the model. The source's `ceiling_entity` is
nominated from an entry that never actually demonstrates a feat, or the source is marked
`unassayed` when it should not be.

### F4. Hard Rule 0: nested truncations inside the feat/description evidence line — minor/cosmetic, VERIFIED

Line 772: `d = " | ".join(re.sub(r"\s+", " ", x)[:150] for x in fl[:3])[:420]` — only the first 3
mined feats per entity are shown (`fl[:3]`), each capped at 150 chars, joined string re-capped at
420. Line 774: `d = re.sub(r"\s+", " ", e.get("description", ""))[:300]`. Line 1138 (phase 2):
`d = re.sub(r"\s+", " ", e.get("description", ""))[:240]`. These are prompt-budget engineering
(defended in nearby comments about token cost) rather than data-loss on write, but they are
literal `[:N]` caps on evidence text the model judges from, which Hard Rule 0 as stated forbids
without exception. Reported per the sweep mandate; lower severity than F3 because no whole
*entity* is excluded, only text within one entity's shown evidence.

### F5. Hard Rule 0: log-only cap hides which sources failed to build — minor, VERIFIED

`phase_write`, line 1804: `for r in refused[:5]:` — the full count is reported correctly
(`"%d source(s) would not build" % len(refused)`, line 1802–1803) but only the first 5 reasons are
printed, so an operator triaging a run with, say, 40 refused sources sees only 5 example errors
and has no way to see whether the other 35 share the same cause or are all distinct.

### F6. Hard Rule 0: log-only cap on grounding-kind summary — cosmetic, VERIFIED

`phase_cosmology`, line 1484: `kinds.most_common(6)` caps the console summary line to 6 distinct
grounding kinds. The underlying `grounds` dict written via `land_json(... GROUNDINGS.json ...)`
(line 1485) is NOT capped — full data lands on disk. Only the human-readable log line is
incomplete if there are more than 6 distinct kinds.

### F7. update_handoff bypasses the project's retry-hardened atomic-write helper — minor, VERIFIED (inconsistency), confidence medium

`update_handoff`, lines 1381–1387:

```python
os.makedirs(os.path.dirname(HANDOFF), exist_ok=True)
tmp = HANDOFF + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    f.write(md)
os.replace(tmp, HANDOFF)
except Exception:
    log("  (handoff update failed: " + traceback.format_exc(limit=1).strip() + ")")
```

Every other landing site in this same file — `save_state` (189), `write_record_catalogue` (465),
`write_record` (567), `land_json`/`_landed` (468–502), and `runguard._land` in the sibling module —
goes through `silence.replace_retry`, which (per its callers' comments elsewhere in this batch)
exists specifically to retry past a transient Windows file-lock rather than raise. `update_handoff`
uses a bare `os.replace` instead. `os.replace` is atomic on both POSIX and Windows, so this is not
a corruption risk, but a transient lock (antivirus scan, a concurrent reader with the file open)
that `silence.replace_retry` would absorb will instead raise here, be caught by the broad
`except Exception` around the whole function, and be logged once with **no retry** — the status
page is simply stale until the next unit completes and calls `update_handoff` again. Low practical
impact (this file is rewritten after every unit, so a miss self-heals soon), but it is an
unexplained inconsistency in a codebase that otherwise treats this exact class of failure as
important enough to build a dedicated retry helper for.

### F8. Name-keyed merge in write_record / write_record_catalogue can conflate duplicate-named entries — HYPOTHESIS, minor-to-major

`write_record`, line 525: `by_name = {e.get("name"): e for e in rec.get("entries") or []}`.
`write_record_catalogue`, line 427: `by = {e.get("name"): e for e in rec.get("entries") or [] if
isinstance(e, dict)}`. Both build a dict keyed purely on `entry["name"]` to merge disk-only
per-entry judgment fields back onto the in-memory copy. If `rec["entries"]` (the in-memory list
being written) contains two or more entries sharing the exact same `name` string — which this same
file's own comment two hundred lines earlier treats as a real, observed hazard class ("`Magic 8
Ball` and `Magic 8-Ball` resolved to one file" — cachekey.py, referenced at line 695–698, albeit a
different normalization bug) — the dict comprehension silently keeps only the **last** entry with
that name; the merge then attaches disk-preserved judgment fields (`category`, `scale_note`,
`magnitude`, `topic`, `catalogued`) to that one survivor only. The earlier duplicate's disk-side
judgment, if any, is not merged onto it (it isn't in `by`/`by_name` at all). Nothing in either
function enforces or checks name-uniqueness within one record's entry list before doing this.
Not verified against a live record known to contain duplicate names — flagged as a plausible latent
hazard given the merge logic's assumption, not a confirmed incident.

---

## src/weave_index.py

### F9. `designations()` cache-hit check does not guard against a `None` signature, unlike its sibling `load_records()` — VERIFIED (asymmetry), minor

```python
def designations(records=None):
    ...
    cacheable = records is None
    sig = _records_sig()[1] if cacheable else None
    if cacheable and _DESIGNATIONS is not None and _DESIGNATIONS[0] == sig:      # line 111
        return _DESIGNATIONS[1]
```
```python
def load_records():
    files, sig = _records_sig()
    if sig is not None and sig == _REC_CACHE["sig"]:                             # line 189
        return _REC_CACHE["out"]
```

`_records_sig()` returns `(files, None)` when `os.path.getmtime` races a deleted file (the
`except OSError` branch at line 176–178). `load_records()` explicitly excludes `sig is None` from
ever counting as a cache hit (line 189: `if sig is not None and ...`). `designations()` has no such
guard (line 111) — if `_records_sig()` returns `None` on two calls in a row (a records directory
that is transiently unavailable, e.g. a network drive hiccup, across two separate calls to
`designations()`), the second call's `_DESIGNATIONS[0] == sig` test is `None == None` → `True`,
and a stale cached designation set is served even though nothing proves the corpus hasn't changed
since. This is exactly the staleness class the function's own docstring says was found and fixed
once already for the same file (BUGS m17, referenced at lines 99–104) — the fix was applied
completely to `load_records()` but the twin cache in the same module was left with the gap.
Severity is minor because the trigger (two consecutive `OSError`s from `_records_sig()`) is a
narrow race, but the asymmetry between the two nearly-identical cache-guard lines is a real,
traceable defect.

### F10. Hard Rule 0: description truncated to 400 chars in the persisted entity index — major, VERIFIED

Line 224, inside `build()`: `"description": (e.get("description") or "")[:400]`. This value is
written into `data/ENTITY_INDEX.json` and (filtered) `data/WEAVE_CANDIDATES.json` via
`silence.write_json` at lines 268–270 — persisted data that the project's own docstring (lines
12–16) says exists specifically so "the model, reading both descriptions, may adjudicate" whether
two same-named entries are the same entity. A disambiguating detail sitting past character 400 of
a long description (not implausible for wiki-sourced entries) is invisible to whatever reads these
files for that adjudication. Unlike the log-only caps below, this is data written to disk and
consumed downstream, not merely a console report.

### F11. Hard Rule 0: console-report-only caps — cosmetic, VERIFIED (underlying files not capped)

- Line 255: `for n in sorted(spread, reverse=True)[:10]:` — "attested in N sources" histogram
  printed to at most 10 rows.
- Line 259: `top = sorted(candidates.items(), key=lambda kv: -len({h["source"] for h in kv[1]}))
  [:18]` — "most cross-attested entities" report limited to top 18.
- Line 264: `', '.join(s[:16] for s in srcs[:5])` — within that top-18 report, only 5 of a
  candidate's sources are named (each truncated to 16 chars), with a `'…'` suffix if more exist.

All three affect only the human-readable `main()` print output; `OUT_INDEX` and `OUT_CAND` (the
actual files written at lines 268–270) contain the full, uncapped data. Reported per the sweep
mandate ("report every one") but these carry no data-loss consequence on disk.

---

## src/runguard.py

### F12. `claim()` is check-then-act, not atomic as a whole — the guard can be won by two concurrent claimants — major, VERIFIED (design gap), confidence high on the code, HYPOTHESIS on real-world frequency

```python
def claim(agent, path=GUARD, note=None):
    prior = read(path)                      # READ
    if holder_is_live(prior):                # CHECK
        ...
        return False, (...)
    now = time.time()
    rec = {"started": now, "heartbeat": now, "done": False, "agent": agent}
    ...
    if not _land(rec, path):                 # ACT (atomic write, but the whole sequence isn't)
        return False, "could not write the guard record"
    return True, "claimed"
```

`_land()` uses `silence.replace_retry`, which makes the individual **write** atomic, but nothing
in `claim()` makes the **read-decide-write sequence** atomic as a unit — there is no exclusive
create, no file lock, no compare-and-swap against the prior content at write time. If two
processes both call `claim()` within the same window (plausible exactly because, per the module's
own docstring, this runs "on a cadence that fires more often than a run takes" — line 102), both
can read `prior` as not-live, both proceed to build and land their own record, and both receive
`(True, "claimed")` back — whichever write lands last on disk silently "wins" the file, but the
other caller has already told its own process it holds the guard and will proceed to do
maintenance work believing it is exclusive. This is the same overlap failure the module's docstring
(lines 5–25) says it exists specifically to prevent (bug m27) — m27's fix (ownership checks in
`beat()`/`release()`, lines 137–141 and 162–167) closes the heartbeat-refresh and release paths
correctly, but the original `claim()` race at the moment of acquisition is not closed by anything
in this file.

**Failure scenario**: an interactive session and a scheduled run both invoke
`runguard.py --claim` within the same second (the file's own history section describes exactly
this kind of overlap already happening once, on 2026-08-24, for the heartbeat case). Both read the
guard as free, both write a claim record, both print `CLAIMED` and exit 0, and both callers proceed
to run the maintenance pass concurrently — the overlap the whole module exists to prevent.

---

## src/module_index.py

### F13. Direct non-atomic write to the generated handoff doc — minor, VERIFIED, outside the letter of the two-writer contract but same class of gap

Lines 75–76:
```python
with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
```

`OUT` is `handoff/MODULE_INDEX.md`. Every comparable output writer examined in this batch — across
`pipeline.py`, `weave_index.py`, and `runguard.py` — writes to a `.tmp` path and lands it via
`silence.replace_retry`/`silence.write_json` or (in one case, F7) `os.replace`. This is the only
file in the batch that writes its output with a plain `open(..., "w")` and no tmp+rename step at
all. `MODULE_INDEX.md` is outside the literal "records/" and "state/" scope the two-writer contract
names, and this module is documented as single-writer ("Generated, never hand-edited"), so this is
not a concurrent-writer hazard in the way records/state files are — but a crash or Ctrl-C mid-write
(or two accidental concurrent invocations) leaves a truncated `MODULE_INDEX.md` on disk with no
recovery, unlike every other generated artifact in this codebase.

---

## Summary table

| # | File:line | Claim | Severity | Confidence |
|---|---|---|---|---|
| F1 | pipeline.py:1408-1413 | chain phase discards harvested rows below 10 and never revisits | blocking/major | VERIFIED |
| F2 | pipeline.py:41 | "forever" docstring vs. non-looping main() | minor | VERIFIED |
| F3 | pipeline.py:765 | `rest[:14]` caps description-only ceiling nomination | major | VERIFIED |
| F4 | pipeline.py:772,774,1138 | nested feat/description truncations in prompts | minor | VERIFIED |
| F5 | pipeline.py:1804 | `refused[:5]` caps failed-build reasons in log | minor | VERIFIED |
| F6 | pipeline.py:1484 | `most_common(6)` caps grounding-kind log summary | cosmetic | VERIFIED |
| F7 | pipeline.py:1381-1387 | update_handoff skips silence.replace_retry | minor | VERIFIED |
| F8 | pipeline.py:427,525 | name-keyed merge can conflate duplicate-named entries | minor-major | HYPOTHESIS |
| F9 | weave_index.py:111 | designations() cache lacks sig-is-None guard | minor | VERIFIED |
| F10 | weave_index.py:224 | description truncated to 400 chars in persisted index | major | VERIFIED |
| F11 | weave_index.py:255,259,264 | console-report-only top-N caps | cosmetic | VERIFIED |
| F12 | runguard.py:98-121 | claim() check-then-act race, two claimants can both win | major | VERIFIED design / HYPOTHESIS frequency |
| F13 | module_index.py:75-76 | non-atomic write of MODULE_INDEX.md | minor | VERIFIED |
| — | catalogue_models.py:158 | see below | major | VERIFIED |

### catalogue_models.py:158 — Hard Rule 0 cap reintroduced two lines after the comment disclaiming it — major, VERIFIED

```python
stale.append({"provider": name, "wants": a, "available_sample": list(r["models"])})   # 151, full list, OK
...
for name in sorted({s["provider"] for s in stale}):
    r = live.get(name)
    if r:
        print(f"  {name}: " + ", ".join(r["models"][:10]))                              # 158, capped
```

The comment at lines 146–150, directly above line 151, explains at length that an earlier `[:8]`
cap on this exact field ("the very field a person reads to pick the replacement for a retired
model name") was identified as a Hard Rule 0 violation and removed — `available_sample` (line 151)
is now genuinely the full list despite its name. Seven lines later, in the same function's
"Current alternatives, per provider" summary print, the same class of cap is reintroduced:
`r["models"][:10]` shows only the first 10 (alphabetically, since `ask_provider` returns
`sorted(ids)`) of a provider's available models when suggesting what to replace a stale model name
with. If the right replacement is the 11th model alphabetically, an operator reading this summary
never sees it — the exact failure mode the file's own comment two screens up says this project
already paid for once and fixed.

**Failure scenario**: a provider serves 30 models; the config's stale reference should be replaced
by a model whose id sorts 15th alphabetically. The printed "Current alternatives" line shows only
the first 10 sorted ids, so the correct replacement is never shown to the person deciding what to
change the config to.
