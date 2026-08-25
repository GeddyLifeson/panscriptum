# Batch 02 — run33
Modules read: pipeline.py (2066 lines), entity_match.py (278 lines), wh40k.py (244 lines), thread_integrity.py (184 lines), ledger.py (136 lines)

## FINDINGS

### 1. pipeline.py:1510-1513 — phase_chain marks itself done without checking whether its write landed  [severity: MAJOR]
`phase_chain` is the one phase in this file that does NOT route through `land_json`/`gate_done` (the
mechanism the file's own `gate_done` docstring says was built specifically to stop this class of bug
at all twelve `land_json` call sites — confirmed: the twelve sites all now gate correctly). It writes
its artifact through a different function and discards the result:

```python
CH.write_result(edges, res, unmatched)   # one schema, one writer -- see chain.write_result
st["done"].setdefault("chain", []).append("all")
```

I checked `chain.write_result` (src/chain.py:91-124) to confirm this is a real gap, not a defensible
omission: it returns `out` (the data dict) unconditionally, regardless of whether the disk write
succeeded — `silence.write_json(...)` failure is only logged to stderr (`silence.note(...)`; `print(...,
file=sys.stderr)`), never raised or surfaced as a return value. So even if the call site checked the
return value, it would get data, not a landed/not-landed verdict. Net effect: if `CHAIN.json`'s write
is denied (a concurrent writer, a locked file — this environment's Windows file-lock issues are a
recorded operational hazard elsewhere in this project), CHAIN.json silently keeps the *previous*
cycle's fit while phase 4 is marked permanently done in `PIPELINE_STATE.json` — no later run will ever
redo it, which is the exact "silent, permanent loss" every other phase in this file was hardened
against.

### 2. pipeline.py:1887-1893 — phase_write can mark itself done on a fully-failed build via vacuous truth  [severity: MAJOR]
```python
landed = []
if jobs:
    ...
    landed.append(land_json(out, jobs))
    ...
gate_done(st, "write", landed)
```
`gate_done` marks the phase done when `all(landed)`. If every "ready" source's
`MB.build_jobs_for_source` call raises (all land in `refused`, none in `jobs`), `landed` stays `[]`,
and `all([])` is `True` in Python — a genuine vacuous-truth trap, not a deliberate check. Phase 8 is
then marked done despite writing no manifest and every source having refused to build, with no
retry recorded anywhere. This is indistinguishable on disk from the legitimate case (nothing needed
building because it was already generated) — the two are conflated by the same empty list.

### 3. pipeline.py:1341-1348 — entrypass's failure-clearing pop is unconditional, contradicting its own comment and its correctly-gated twin in phase_synthesis  [severity: MAJOR]
```python
if landed and all(entry_settled(e) for e in batch):
    if key not in done_keys:
        done_keys.append(key)
elif not landed:
    log(f"    batch {key} judged in full but its write was denied - left open")
else:
    log(f"    batch {key} returned {sum(...)}/{len(batch)} - left open for retry")
st.get("failed", {}).get("entrypass", {}).pop(key, None)   # see phase 1: a later
# success retires the earlier failure, so the failed-set stays a list of things
# actually still broken rather than a scar log.
```
The `pop()` fires on every path through this block — including the "write was denied" branch and the
"left open for retry" (partially-judged) branch, both of which are failures, not successes. Compare
`phase_synthesis` about 400 lines earlier, which gets this right: there the pop is reached only after
`if not write_record(path, rec): ...; continue`, i.e. only on an actual landed write. Here, any
non-`None` model answer clears a prior "ollama failure" record from `st["failed"]["entrypass"]` even
when the write that round was denied or the judgment incomplete — and no new failure entry is ever
recorded for "write denied" or "partial" (those only get a `log()` line). Consequence: a batch that
keeps failing to land (e.g. a source under sustained write contention) can sit with **zero** entries
in `st["failed"]`, which is exactly the count `update_handoff` surfaces to the owner as "Failures
logged" in `handoff/RUN_STATUS.md` — the health signal this project explicitly relies on for
unattended, multi-day runs goes quiet exactly when it should be loudest.

### 4. thread_integrity.py:58-63 vs weave_index.py:146-162 — `load_entities()` normalizes names differently than the module that produced the keys it checks them against, so continuity-qualified entities register as false DANGLING  [severity: MAJOR]
`thread_integrity.load_entities()` builds its per-source entity-key sets with:
```python
k = re.sub(r"[^a-z0-9]", "", re.sub(r"\([^)]*\)", "", (e.get("name") or "").lower()))
```
— this **unconditionally strips every parenthetical**, with no continuity marker preserved. But the
keys it checks those sets against in `classify()`'s DANGLING branch (`k not in ents.get(a, ())`) come
from `data/WEAVE_CANDIDATES.json`, which is built by `weave_index.py`'s own `norm()`:
```python
def norm(name):
    """... A declared continuity survives the fold as a suffix, so two Thors stay two Thors."""
    keep = continuity_of(name)          # e.g. "earth16" for "Wally West (Earth-16)"
    ...
    return s + "@" + keep if keep else s
```
For any name carrying a recognized continuity qualifier (`continuity_of` checks against a real
designation list — "Earth-16" is entity_match.py's own headline example of why this distinction
matters), `weave_index.norm` produces `"wallywest@earth16"` while `thread_integrity.load_entities`
produces plain `"wallywest"`. These never compare equal. So in `classify()`'s DANGLING check, every
shared key built from a continuity-qualified name will read as "not in `ents[source]`" **even when the
entity is genuinely still there**, because the two modules are comparing keys from two different,
independently-maintained folding schemes over what is supposed to be the same key space. Since
DANGLING fires when *all* of a pair's shared keys read as gone, a pair whose only shared entities
happen to carry continuity qualifiers will be misreported as DANGLING (weave drift) when nothing has
actually drifted — corrupting the one signal this module exists to produce, on exactly the class of
name (Wally-West-style disambiguated continuities) the rest of the project treats as its hardest case.

## Ranked lower — MINOR / INFO

### 5. pipeline.py:1885-1886 — `refused[:5]` truncates the diagnostic log of sources that would not build  [severity: MINOR]
```python
for r in refused[:5]:
    log("    refused: %s" % r)
```
Only a log line is capped (the full `refused` list is still counted correctly in the summary line and
nothing downstream loses data from this), so this isn't the kind of roster truncation Hard Rule 0
targets — but it is the one place in this batch where a list gets a bare `[:N]` slice with no
"truncated" marker, in a codebase that is otherwise scrupulous about flagging exactly that (see
`entity_match.candidates`'s `truncated` field for the pattern this omits).

### 6. pipeline.py:1462-1466 — `update_handoff` writes `RUN_STATUS.md` via a bare `os.replace`, not `silence.replace_retry`  [severity: MINOR]
Every other artifact write in this file (`save_state`, `write_record`, `write_record_catalogue`,
`land_json`) goes through `silence.replace_retry` for exactly the Windows file-lock contention this
project has hit before. This one call site uses `os.replace(tmp, HANDOFF)` directly. It is caught by
the surrounding `try/except Exception` in `update_handoff` and logged rather than crashing, and the
file is rewritten again after the very next unit, so the practical exposure looks small — but it is
the only artifact write in the file with no retry, in a file whose header comment is itself an essay
on what happens when two writers of one file disagree.

## QUESTIONS

1. **pipeline.py:1986 — `_ESC.assert_clear()` is checked exactly once, at the top of `main()`, before
   the phase loop starts — never again during the run.** `phase_entrypass` alone is documented
   "Multi-day; fully resumable," and the whole `for ph in phases` loop can carry the process through
   several phases without returning to `main()`. If a SUPERVISOR- or OWNER-level halt is raised while
   this process is already inside a long phase, nothing in this file re-checks it before the next
   `save_state`/unit completes. Is halt-propagation for an in-flight run expected to come from outside
   this process (e.g. a supervisor that kills the PID), or should phases re-check the gate
   periodically? I did not read `escalation.py` (out of this batch) so I can't rule out a mechanism
   living there.

2. **thread_integrity.py:118 — the `recorded is not None` branch of `classify()` only checks
   `(b, a) in recorded` for RECIPROCAL, never `(a, b) in recorded`.** This branch is unreached today
   (`main()` always calls `classify(..., recorded=None)`, and the docstring says the directed graph
   "does not exist until the owner's Step 4 entanglement pass"), so I'm not flagging it as a live bug.
   But when that pass exists and this branch activates, a single recorded direction would be enough to
   call a pair RECIPROCAL without ever confirming the *other* direction is also recorded. Is checking
   one direction intentional (e.g. because of how `pairs` gets deduplicated to one canonical ordering
   before this runs), or is this an incomplete stub that needs the second check added before it goes
   live?

3. **pipeline.py:189 — `save_state` discards the boolean `silence.replace_retry(tmp, STATE)` returns.**
   Unlike `write_record`/`write_record_catalogue`/`land_json` (all gated via `_landed`), `save_state`
   doesn't check whether `PIPELINE_STATE.json` actually landed. Given `save_state` is called after
   nearly every unit and always writes the *whole* current `st` dict, a single transient failure looks
   self-healing (the next successful call carries the same in-memory progress forward) — which is
   probably why this one wasn't hardened. Worth confirming that reasoning is actually why, versus an
   oversight that happens to be low-consequence.

## CLEAN

- **entity_match.py** — read in full. `qualifier_compatible`, `similarity`, `candidates`, `best` all
  checked against the module's own stated invariants (the Wally West / Earth-16 continuity trap);
  logic holds. Confirmed via grep that nothing in `src/` calls this module except `verify_math.py`,
  which matches the module's own header ("nothing calls this module yet") — not dead code, a
  deliberately unwired proposal seam.
- **wh40k.py** — read in full. Data-heavy module (Warhammer 40K Assay roster); `compute()` and
  `main()`'s ranking/printing logic hold up, and the file's own write is already atomic
  (`silence.write_json`), fixed as noted in its own comment referencing the `zfighters.py` sibling.
- **ledger.py** — read in full. Verified `to_standards`/`from_standards` are true inverses,
  `cross_rate`'s algebra (`rb/ra`) is correct, and `assay_to_standards`'s interpolation direction is
  correct against `assay.LADDER`'s actual (ascending) order and `assay.BAND_EDGES`'s monotonically
  increasing ruin figures — checked both directly rather than assuming.
- **thread_integrity.py** — read in full; one finding (4, above) and one question (2, above) about
  it; the currently-live code path (`recorded=None`, `implied_threads`, the DANGLING gate's happy
  path) is otherwise sound.
- **pipeline.py** — read in full; findings 1-3, 5-6 and questions 1, 3 above. Everything else checked
  and held: all twelve `land_json` call sites gate correctly through `gate_done` (the historical bug
  the docstring describes is genuinely fixed everywhere except the `chain.py`-routed one in finding
  1); `write_record`/`write_record_catalogue`'s merge-on-drift logic is sound in both directions;
  `valid_scale_note`'s four gates and `clean_band`/`ceiling_band`'s deliberate strict/lax asymmetry
  are correctly reasoned and match their own long comments; `batch_settled`/`entry_settled` correctly
  unify the two resume gates the file's own comment says used to disagree.
