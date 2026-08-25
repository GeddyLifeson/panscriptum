# SWEEP 31 — BATCH 08 AUDIT

**Modules:** `src/feats.py` (1006 lines), `src/zfighters.py` (485 lines), `src/tiers.py` (360
lines), `src/cosmography.py` (283 lines), `src/wh40k.py` (245 lines),
`src/recover_folder_records.py` (180 lines), `src/retry_synthesis.py` (164 lines)

**Total lines read: 2,723** (every line of all seven files, plus targeted cross-reference reads
of `src/pipeline.py:294-420,713-812`, `src/silence.py:263-350`, and `src/assay.py` LADDER/
BAND_EDGES definitions to check claims made in this batch's docstrings against the code they
describe).

Read-only audit. No files were modified. No long-running or state-mutating scripts were run —
only `Read`, `Grep`/`grep`, and directory creation for this report.

---

## FINDING 1 — `retry_synthesis.py:56-91` (`synthesise()`) — reintroduces the exact ceiling-clamp
bug the owner ruled "FIX IT ALL" on (m13), and the docstring claiming parity is false

**Claim:** `synthesise()` is NOT "byte-identical prompt construction to phase_synthesis" as its
own docstring (line 57-58) asserts. It silently reintroduces the single-sample-of-14 ceiling
clamp that `pipeline.py`'s `phase_synthesis` was explicitly fixed to stop doing.

**Why it is wrong:**
```python
# retry_synthesis.py:60
sample = sorted(rec["entries"], key=lambda e: -len(e.get("description", "")))[:14]
```
This takes ONE ranked-then-truncated sample of 14 entries, ranked by raw description length, and
never looks at mined feats at all. Compare `pipeline.py:751-793` (`phase_synthesis`), which was
rewritten specifically to stop doing this:
```python
# pipeline.py:756-765
# EVERY feat-bearing entry is nominated, fourteen per call, best band across chunks
# wins. The fixed sample-of-14 could silently clamp a whole source to a lesser
# ceiling whenever the true strongest entity ranked fifteenth by feat-count -- and
# the clamp then cut that entity's own later evidence down to the wrong band (BUGS
# m13, Hard-Rule-0-shaped, ruled by the owner 2026-08-24: FIX IT ALL). ...
chunks = [with_feats[i:i + 14] for i in range(0, len(with_feats), 14)] or [rest[:14]]
best = None
for ci, sample in enumerate(chunks):
    ...
    if best is None or r_ > best[0]:
        best = (r_, g, b)
```
`phase_synthesis` chunks **every** feat-bearing entry across as many 14-entry calls as needed and
takes the best band across all chunks. `retry_synthesis.py`'s `synthesise()` does neither: it
takes a single top-14-by-description-length slice (feats aren't even consulted for ranking) and
asks one question. This is precisely the "fixed sample-of-14" pattern the pipeline's own comment
names as Hard-Rule-0-shaped and says was ordered fixed everywhere.

**Failure scenario:** Any of the twelve sources this script exists to retry (Dragon Ball Z, Dune,
etc. — sources named in this file's own module docstring) whose true ceiling entity has a short
catalogue description but ranks past position 14 by description length will never be shown to the
model at all, let alone ranked by its actual feats. The retried source is scored by a strictly
weaker method than every neighbour the main pipeline synthesised — the exact asymmetry the
docstring claims does not exist ("so a retried source is not scored by a different method than
its neighbours").

**Severity:** blocking (reintroduces a bug the owner explicitly ordered eliminated everywhere;
silently produces wrong ceiling/band data for the retried sources).
**Confidence:** VERIFIED — traced both functions side by side; the divergence is unambiguous.

---

## FINDING 2 — `retry_synthesis.py:43-47` (`save_side()`) — bare tmp+`os.replace`, not
`silence.write_json`/`replace_retry`; exactly the hazard class the project's own sweep fixed

**Claim:** `save_side()` writes the shared state file `data/SYNTHESIS_RETRY.json` with the
project's own named-and-fixed anti-pattern instead of the sanctioned writer.

```python
# retry_synthesis.py:43-47
def save_side(d):
    tmp = SIDE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    os.replace(tmp, SIDE)
```
Compare `silence.write_json`'s own docstring (`silence.py:290-309`), which describes this
*exact* pattern as the fault it exists to replace project-wide:
> "Found by the 2026-08-25 comprehensive sweep: TWELVE call sites across ten modules were writing
> shared `data/` and `state/` files with a bare `open(path, "w")` + `json.dump`... THE TMP NAME
> CARRIES PID AND THREAD, which the older hand-rolled `path + ".tmp"` sites did not... Never
> raises on a denied replace: `replace_retry` records it and the caller's write lands next round."

`save_side` has neither protection: its tmp name is not PID/thread-unique, and `os.replace` here
is called bare — a `PermissionError` (the documented Windows collision, e.g. a concurrent reader
or the `--merge` invocation) propagates uncaught and kills the run, rather than backing off and
retrying as `silence.replace_retry` does.

**Failure scenario:** the retry loop (`main()`, line 147-156) calls `save_side(side)` after every
single successful synthesis. If any reader (a dashboard, a concurrent invocation, an AV scanner —
the same collision `silence.replace_retry`'s docstring cites as having taken an assay worker down
on 2026-08-23) holds `SYNTHESIS_RETRY.json` open at that instant, this call raises and the whole
retry run aborts with an unhandled exception, losing whatever result was about to be persisted for
that source and requiring a full restart of `main()` for the remaining `todo` list.

**Severity:** major.
**Confidence:** VERIFIED — pattern compared directly against the project's own documented
before/after hazard description.

---

## FINDING 3 — `feats.py:349-369` (`discover()`) — MediaWiki `aplimit`/`srlimit` truncate
discovery and no continuation is followed; self-diagnosed as open but not fixed

**Claim:** Despite the docstring's Hard-Rule-0 framing ("the truncation is gone"), `discover()`
still asks MediaWiki for at most 500 `allpages` subpages and 50 `search` hits and never follows
the `continue` token either API returns, so an entity with more evidence pages than that is read
in part.

```python
# feats.py:349-350
ap = api(host, {"action": "query", "list": "allpages",
                "apprefix": f"{name}/", "aplimit": "500"})
if (ap or {}).get("continue"):
    _CAP_BOUND["aplimit"] = _CAP_BOUND.get("aplimit", 0) + 1
...
# feats.py:359-362
sr = api(host, {"action": "query", "list": "search", "srlimit": "50",
                "srsearch": f"{name} power abilities strength feats"})
if (sr or {}).get("continue"):
    _CAP_BOUND["srlimit"] = _CAP_BOUND.get("srlimit", 0) + 1
```
The module's own header comment (lines 76-86) frames this candidly as an open question ("Nothing
measured how often that happens... Reported in roll()'s summary") and `roll()` (lines 919-924)
does print how often `_CAP_BOUND` triggers. But printing a count after the fact is a measurement,
not a remedy — the fetch for that entity on that run is still partial, which is the exact
"smaller universe wearing the same shape as the real one" Hard Rule 0 names. The `extra` parameter
removal earlier in the same function (lines 316-328) fixed one truncation (post-hoc ranking then
slicing) while this pre-existing API-level truncation, on the same function, was left standing.

**Failure scenario:** an entity with 501+ subpages under the `Name/` prefix, or whose search
query returns 51+ qualifying hits, has its evidence set silently short by whatever falls after
the API's own limit — same failure class as the fixed `extra=25` bug, just one layer further in.

**Severity:** major (policy gap; already disclosed via `_CAP_BOUND` but not remedied).
**Confidence:** VERIFIED — no continuation loop exists in `discover()` or `api()`.

---

## FINDING 4 — `tiers.py:243-248` (`chart()`) — a missing/corrupt `GROUNDINGS.json` is
indistinguishable from "everything is legitimately ungrounded"

**Claim:** `chart()` catches every exception from loading `data/GROUNDINGS.json` and silently
substitutes an empty dict, which then reads as "no source has any grounding evidence" rather than
"the grounding data could not be read this run" — the exact transport-failure-as-verified-absence
pattern this sweep targets, and the opposite of the fail-closed doctrine `CLAUDE.md`'s Hard Rule
-1 states for this project ("An unreadable config... missing COVERAGE.json... all refuse. Silence
must never authorise anything.").

```python
# tiers.py:243-248
try:
    with open(os.path.join(HERE, "data", "GROUNDINGS.json"), encoding="utf-8") as f:
        _groundings = json.load(f)
except Exception:
    silence.note("tiers.py:245")
    _groundings = {}
```
With `_groundings = {}`, every call to `hyperverse_of(s, _groundings)` (line 258) and every group
passed through `xenoverse_grounding(tiers["xenoverse_groups"], _groundings)` (line 261) resolves
to `"ungrounded"` for the whole corpus — `chart()` then writes a full `TIERS.json` (via `main()`,
line 354) that looks like a completed run in which no source has a cosmogony, when the real state
is "the grounding file could not be opened or parsed this run."

**Failure scenario:** `data/GROUNDINGS.json` is transiently locked by a concurrent writer,
briefly truncated mid-write by another process, or simply absent on a machine that hasn't run the
grounding pass yet — `chart()` proceeds anyway and lands a `TIERS.json` in which the hyperverse
grounding for every xenoverse reads `"ungrounded"`/`contested_by: []`, silently discarding
whatever real grounding data exists, rather than halting per Hard Rule -1's escalation chain.

**Severity:** major.
**Confidence:** VERIFIED for the mechanism (silent fallback on any exception); HYPOTHESIS for how
often the file is actually unavailable in practice.

---

## FINDING 5 — `recover_folder_records.py:143-160` — records written directly to
`data/records/*.json`, bypassing the two-writer contract; self-acknowledged, still open

**Claim:** This script writes record files with `silence.write_json(path, record, ...)` directly
against `RECORDS = data/records`, not through `pipeline.write_record` / `write_record_catalogue`
as the project's two-writer contract requires.

```python
# recover_folder_records.py:143-159
path = os.path.join(RECORDS, slug(name) + ".json")
if not args.dry_run:
    # ATOMIC. NOTE FOR REVIEW: the two-writer contract says a RECORD should be written
    # through `pipeline.write_record_catalogue`, not straight to disk at all. Making the
    # write atomic is the safe half of that repair; routing this recovery tool through
    # the catalogue writer changes its merge semantics and is flagged in NEXT_STEPS.
    ...
    if not silence.write_json(path, record, indent=2, ensure_ascii=False):
        ...
```
The comment is explicit that this is a known, deliberately-deferred violation ("flagged in
NEXT_STEPS"), and the write is at least atomic and gated on success. Reporting it anyway per this
sweep's instructions to record every instance of the pattern, however previously flagged.

**Failure scenario:** if `pipeline.write_record_catalogue` has merge/validation logic this script
does not replicate (e.g. de-duplicating entries against a record written by another writer for
the same source between this script's read and write), a record produced by this path could
diverge from what the catalogue writer would have produced — the exact class of hazard the
contract exists to prevent, even though this specific script only creates records for sources
that had none.

**Severity:** minor (self-flagged, atomic, narrow blast radius — only fires for `entry_count: 0`
sources with no existing record).
**Confidence:** VERIFIED, and already known to the codebase's own authors.

---

## FINDING 6 — `recover_folder_records.py:162-164` — `data/SWEEP_ROLL.json` read-modify-write
race; self-acknowledged elsewhere in the codebase

**Claim:** `main()` loads the whole roll list, mutates `roll_entry` dicts in place across the
`empty` loop, and writes the entire list back at the end with no re-read/merge against the file
as it stands on disk at write time.

```python
# recover_folder_records.py:86, 162-164
roll = load(ROLL)
...
if not args.dry_run and written:
    # ATOMIC: `resync_roll.py`'s docstring names THIS script as a roll-clobber source.
    silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)
```
The write itself is atomic (via `silence.write_json`), but the read-modify-write over the whole
roll is not merge-safe: if another writer updates `SWEEP_ROLL.json` between this script's `load()`
and its final write, those updates are silently overwritten by this script's in-memory copy — the
comment cites `resync_roll.py`'s own docstring as already naming this script as a clobber risk.

**Severity:** minor (already documented elsewhere as a known risk; this script is typically run
standalone rather than concurrently with the main pipeline).
**Confidence:** VERIFIED mechanism; self-acknowledged in adjacent code.

---

## FINDING 7 — `feats.py:693-702` (`axis_evidence()`) — dead code

**Claim:** `axis_evidence()` has no callers anywhere in the repository.

Verified with `grep -rn "axis_evidence" src` (recursive, all `.py`): the only match is the
function's own definition at line 693. `by_axis()` (lines 705-728) implements the same three
gates inline instead — its own comment (lines 717-720) explains this was a deliberate hoist for
performance ("a 3x regex redundancy over an 874MB corpus... Hoisted"), which superseded
`axis_evidence()` without removing it.

**Severity:** cosmetic (no behavioral effect; risk is future drift between the two copies of the
same gate logic if one is edited and the other isn't).
**Confidence:** VERIFIED by grep.

---

## Modules read with no findings worth reporting

- **`cosmography.py`** — pure computation module (no file I/O, no shared state). Traced
  `kardashev_to_magnitude()`'s band-selection loop against `assay.LADDER`'s actual ordering
  (`["M0"..."M10"]`, ascending) and `validate()`'s ceiling checks; both are correct. No caps, no
  swallowed exceptions, no two-writer surface.
- **`wh40k.py`** — hand-authored data + `silence.write_json` output; already uses the sanctioned
  atomic writer (explicitly noted in its own comment as the "m100 tail" fix). No caps, no
  swallowed exceptions.
- **`zfighters.py`** — same shape as `wh40k.py`; already uses `silence.write_json`. The one
  `except Exception: silence.note(...)` (loading Goku's sheet from a sibling file) degrades to
  "Goku absent from ranking" rather than masquerading as a false positive/negative, and is
  consistent with its own comment.

---

## Summary table

| # | File:line | Severity | Confidence |
|---|---|---|---|
| 1 | retry_synthesis.py:56-91 | blocking | VERIFIED |
| 2 | retry_synthesis.py:43-47 | major | VERIFIED |
| 3 | feats.py:349-369 | major | VERIFIED |
| 4 | tiers.py:243-248 | major | VERIFIED (mechanism) |
| 5 | recover_folder_records.py:143-160 | minor | VERIFIED |
| 6 | recover_folder_records.py:162-164 | minor | VERIFIED |
| 7 | feats.py:693-702 | cosmetic | VERIFIED |
