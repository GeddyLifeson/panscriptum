# Sweep 28 — Batch 02 Audit

Modules: `src/pipeline.py` (1909 lines), `src/anchors.py` (250 lines), `src/coverage.py`
(191 lines), `src/repass_bands.py` (119 lines). All four read in full, line by line, no sampling.

`NEXT_STEPS.md` §3 read first. Relevant KNOWN items for this batch:
- `coverage.py:10-18 vs :82-115` — docstring promises 5 states incl. UNREACHABLE; `state_of()`
  returns 4.
- `anchors.py` — instrument floor→ceiling invariant violated, exits 1.
- `pipeline.py:521` — `write_record`'s drift-merge gated on entry count only. `:1327
  update_handoff` uses raw `os.replace`.

All four KNOWN items were re-verified live this run (re-read the source, and for `anchors.py`
re-ran the script). All four are STILL OPEN, findings below record current evidence.

---

## src/pipeline.py (1909 lines)

### HIGH — NEW — truncated-name cache-path collision corrupts mined feats between distinct entities
`pipeline.py:634-636`, inside `_mined_feats()`:
```python
hd = re.sub(r"[^A-Za-z0-9]+", "_", host)[:40]
for e in rec["entries"]:
    nd = re.sub(r"[^A-Za-z0-9]+", "_", e["name"])[:80] + ".json"
    for base in (os.path.join(HERE, "data", "readfeats"), os.path.join(HERE, "data", "feats")):
        fp = os.path.join(base, hd, nd)
```
The entity name is sanitized and truncated to 80 characters to build the cache-file path — the
same pattern as `coverage.py:44-46` (see that module's matching HIGH finding; this is one bug
appearing in two files, per lesson 14: "when you fix a shape, grep the tree for it"). Two
distinct catalogued entries in the same source whose sanitized names agree on the first 80
characters collide on one file.

**Verified live** against the current corpus (`data/records/*.json`): 5 real within-source
collisions exist today, e.g. source "all Pixar films" has both `Magic 8 Ball` and `Magic 8-Ball`
as distinct entries, both sanitizing to `Magic_8_Ball.json`. Confirmed on disk:
`data/feats/pixar_fandom_com/Magic_8_Ball.json` is a single file. Other live collisions found:
`Pantheon: Norse` (`Vör`/`Vör` — mojibake variants), `Rime of the Frostmaiden`
(`Ten Towns`/`Ten-Towns`), `The Binding of Isaac` (`Infested!`/`Infested?`), `Western astrology`
(`Midheaven (Medium Coeli / MC)`/`Midheaven (Medium Coeli, MC)`).

**Failure scenario:** `_mined_feats(rec)` for "all Pixar films" reads
`data/feats/pixar_fandom_com/Magic_8_Ball.json` for BOTH `Magic 8 Ball` and `Magic 8-Ball`, and
hands whichever feats that one file holds to `phase_synthesis`'s ceiling-nomination prompt under
BOTH entity names — one entity's mined evidence is silently attributed to a different named
entity in the source's ceiling nomination. Same root cause corrupts `coverage.py`'s citation
counts (see that module's finding) since `state_of()` shares the identical path-building logic.

### HIGH — KNOWN, STILL OPEN — `write_record`'s drift-merge is gated on entry count only
`pipeline.py:518-522`:
```python
merged = rec
try:
    with open(path, encoding="utf-8") as f:
        disk = json.load(f)
    if len(disk.get("entries") or []) != len(rec.get("entries") or []):
        # ... per-entry field merge onto disk copy ...
```
The merge path only triggers when the entry COUNT differs. If a concurrent writer (the
catalogue side, `write_record_catalogue`) changes per-entry field CONTENT — e.g. re-catalogues
and revises a `magnitude`/`topic`/`scale_note` on existing entries — without changing the total
entry count, the `!=` check is False, `merged` stays `rec` (this process's stale in-memory
copy), and the disk's newer content is silently overwritten with no merge and no log line.
**Failure scenario:** process A loads a 500-entry record, holds it in memory for an hour running
phase 2 on other sources. Process B (catalogue) re-corrects 30 entries' topics in that same
500-entry record (count unchanged). Process A finishes its own unrelated unit and calls
`write_record` on its still-500-entry in-memory copy — B's 30 corrections vanish, with no error,
no log, and no distinguishing trace from a normal successful write.

### MED — KNOWN, STILL OPEN — `update_handoff` writes with a raw `os.replace`
`pipeline.py:1323-1327`:
```python
os.makedirs(os.path.dirname(HANDOFF), exist_ok=True)
tmp = HANDOFF + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    f.write(md)
os.replace(tmp, HANDOFF)
```
Every other writer in this file (`save_state`, `write_record`, `write_record_catalogue`,
`land_json`, via `_landed`) routes through `silence.replace_retry`, which retries on the
transient Windows file-lock failures this project has hit repeatedly elsewhere (AV scanners,
a reader mid-open). This one site uses a bare, unretried `os.replace`, so a transient lock
during `RUN_STATUS.md`'s frequent (per-unit) rewrite can raise and — per the `except Exception:`
two lines below — silently swallow into a one-line log entry, leaving `RUN_STATUS.md` stale
with no retry.

### MED — NEW — `refused[:5]` truncates a real diagnostic (Hard Rule 0 shape)
`pipeline.py:1744-1747`, `phase_write`:
```python
log("  manifest: %d job(s) across %d source(s), %d source(s) would not build"
    % (len(jobs), len(names), len(refused)))
for r in refused[:5]:
    log("    refused: %s" % r)
```
`refused` holds `"%s (%s)" % (src, type(e).__name__)` for every source whose manifest build
raised. The count is reported in full, but only the first 5 individual reasons are ever logged
— if 30 sources fail to build (e.g. a systemic exception from `MB.build_jobs_for_source`), the
operator sees "30 source(s) would not build" and only 5 of the actual `(src, exception-type)`
pairs, with no way to tell whether the remaining 25 share the same cause or are 25 different
problems. This is exactly the shape lesson 16 warns about: a cap on a diagnostic, not the data.

### LOW/MED — NEW — model-generated evidence/rationale/scale_note silently truncated with no disclosure
`pipeline.py:745-746`:
```python
"evidence": (got.get("evidence") or "").strip()[:600],
"rationale": (got.get("rationale") or "").strip()[:900],
```
and `pipeline.py:1136,1138`:
```python
batch[i]["scale_note"] = sn[:500]
...
batch[i]["scale_note_rejected"] = raw[:500]
```
These truncate the model's generated text to a hard character cap with no flag recorded when
truncation actually occurs (contrast `ingest_doc.py:216`, already flagged in NEXT_STEPS for the
identical "hard-truncated, no disclosure" shape). The system prompts ask for terse output ("at
most 20 words" / "at most 15 words"), so in practice the caps rarely bite — but nothing in the
record distinguishes "the model was terse" from "the model wrote more and it got cut," so a
future reader of a record with e.g. a 600-char `evidence` field cannot tell whether that is the
whole quote or a truncated one.

---

## src/coverage.py (191 lines)

### HIGH — KNOWN, STILL OPEN — docstring promises 5 states, `state_of()` only returns 4
`coverage.py:10-18` (docstring):
```
CITED        ...
READ         ...
NO PAGE      the wiki has no article under this name
NO HOST      the source has no wiki at all
UNREACHABLE  a host exists but the fetch failed -- the only state that is purely a defect
```
`coverage.py:82-115`, `state_of()`:
```python
def state_of(host, name):
    if not host:
        return "NO HOST", 0, 0
    cache = _so_load()
    best = ("NO PAGE", 0, 0)
    for base in (READ_CACHE, F.CACHE):
        fp = _p(base, host, name)
        try:
            mt = os.path.getmtime(fp)
        except OSError:
            continue
        ...
    return best
```
There is no branch anywhere in this function that can produce `"UNREACHABLE"`. A host that
exists but whose fetch genuinely failed leaves no cache file on disk, which is indistinguishable
here from "no article under this name" — both fall through to the `best = ("NO PAGE", 0, 0)`
default. Re-verified this run: `grep -c UNREACHABLE coverage.py` → 2 hits, both inside the
docstring; zero in the executable code. The distinction the file's own opening paragraph calls
"the whole point of the file" (collapsing READ vs NO PAGE) is not even implemented for the
fetch-failure case the docstring names as "the only state that is purely a defect."

### HIGH — NEW — `_p()`'s 40/80-char truncation collides distinct entities onto one cache file
`coverage.py:44-46`:
```python
def _p(base, host, name):
    return os.path.join(base, re.sub(r"[^A-Za-z0-9]+", "_", host)[:40],
                        re.sub(r"[^A-Za-z0-9]+", "_", name)[:80] + ".json")
```
Same collision as `pipeline.py:634-636`'s `_mined_feats` (one bug, two files — see that
finding for the live-verified collision list: "Magic 8 Ball"/"Magic 8-Ball" in "all Pixar
films" both resolve to `data/feats/pixar_fandom_com/Magic_8_Ball.json`, plus 4 more live
examples found by scanning every record for entries whose sanitized 80-char name matches
another distinct entity in the same source).

**Concrete failure scenario for `measure()`:** if `Magic 8-Ball`'s page was fetched and cited
(feats present) but `Magic 8 Ball` was never fetched, `state_of(host, "Magic 8 Ball")` reads the
same `Magic_8_Ball.json` file and returns `"CITED"` for an entity that was never actually
researched — `measure()`'s per-source `cited`/`coverage` counters silently credit citation
coverage that does not exist for that entity. This is the "truncated string used as a dict key"
shape already flagged for `chain.py:354`, now confirmed present here too and reproduced against
live data rather than only reasoned about.

### MED — NEW — `_so_load()` swallows ANY exception, comment claims a narrower exemption
`coverage.py:57-65`:
```python
def _so_load():
    if not _SO["loaded"]:
        try:
            with open(_SO_CACHE_P, encoding="utf-8") as f:
                _SO["d"] = json.load(f)
        except Exception:
            _ = "silence-exempt: no cache yet is the normal first state"
        _SO["loaded"] = True
    return _SO["d"]
```
The comment justifies the swallow as "no cache yet is the normal first state" — but the `except
Exception` also catches a corrupted/truncated `state/coverage_cache.json` (e.g. a torn write
from a concurrent `_so_save()`, or disk corruption), which is a genuinely different situation
the comment does not cover, and neither `silence.note` nor `log` is called for that case (unlike
the sibling `_so_save`, which does call `silence.note` on its own save failure two functions
below). Impact is bounded — `state_of()` recomputes correctly from the underlying evidence files
on any cache miss, so this costs performance (every entry re-parses once) rather than wrong
output — but the comment describes a narrower condition than the code actually implements
(lens 6: comment/code mismatch), and a real corruption event would be invisible.

### MED — NEW — hardcoded/uncapped-by-default diagnostic caps in `report()`, one with no override
`coverage.py:161`:
```python
print("\nSOURCES WITH NO WIKI HOST — nothing can ever be cited here")
for r in sorted((x for x in rows if not x["host"]), key=lambda x: -x["entries"])[:12]:
```
`coverage.py:171`:
```python
print("\nBEST COVERED")
for r in sorted(have, key=lambda x: -x["coverage"])[:10]:
```
Both are Hard Rule 0-shaped diagnostic caps (lesson 16: "a cap on a diagnostic hides the
pattern, not just the rows"). **Verified live against the current corpus:** 15 sources currently
have no wiki host (`hosts.get(source)` falsy), but this report only ever prints 12 of them — 3
are silently absent from every run's terminal output. The `--show` CLI flag only threads through
to the "WORST COVERED" loop at line 166; the "NO WIKI HOST" cap at 161 and the "BEST COVERED"
cap at 171 have no override at all, hardcoded regardless of corpus size. (The underlying
`COVERAGE.json` write at the bottom of `main()` is NOT capped — this is specifically the
terminal report, which is nonetheless the thing a human actually reads to decide what to work
on next.)

---

## src/repass_bands.py (119 lines)

### MED — NEW — hardcoded source-count "of 211" is already stale
`repass_bands.py:97-98`:
```python
print("\nSOURCE CEILINGS")
print(f"  demoted to unassayed: {len(demoted_sources):,} of 211")
```
`211` is a literal, not derived from `len(recs)` (the actual list this function iterates,
returned by `PL.records()` two lines earlier at line 36). **Verified live:** `PL.records()`
returns 210 sources today (confirmed by direct call: `len(pipeline.records())` → 210), not 211
— already off by one, and will silently drift further every time a source gains its first
entries, loses all its entries, or a new source is catalogued, since nothing recomputes this
number. A maintainer reading "3 of 211" has no way to know the denominator is wrong without
independently counting the records directory.

### LOW — NEW, minor — sample print caps, but honestly labeled and the real counts are uncapped
`repass_bands.py:102,108`:
```python
print("\n  SURVIVORS — every one of these is an act upon an object, or a measured quantity:")
for s, n, b, sn in kept_entries[:14]:
...
print("\n  DEMOTED — a sample of what was carrying a Magnitude:")
by_band = collections.Counter(b for _, _, b, _ in demoted_entries)
print(f"     by band: {dict(sorted(by_band.items()))}")
for s, n, b, sn in demoted_entries[:8]:
```
Unlike the other diagnostic caps in this batch, these are explicitly labeled as "a sample" in
the adjacent print text, and the totals (`total_banded`, `len(kept_entries)`,
`len(demoted_entries)`) plus the full `by_band` Counter breakdown are computed over the
COMPLETE, uncapped lists — the pattern lesson 16 warns about (an undercount masquerading as
complete) is not present here since nothing downstream relies on the capped sample and the
labeling is honest. Noting for completeness only; not recommending action.

---

## src/anchors.py (250 lines)

### HIGH — KNOWN, STILL OPEN — floor→ceiling invariant violated (re-run live this session)
Ran `python src/anchors.py` directly this session (`REAL EXIT:1`, confirming the exit-code fix
documented in the file's own `__main__` comment at `:236-248` is genuinely in effect — the
script no longer silently exits 0 on a violated invariant, unlike the state NEXT_STEPS'
lesson 9 describes for the pre-fix version).

The invariant itself remains violated, confirmed with current live numbers:
```
monotone floor -> ceiling : False
   The Skate Guy                  0.22
   A Sword                        0.10
   Yggdrasil                      6.18
   Goku                           5.42
   The Seat of the Creator       10.99
```
`A Sword` (0.10) sits below `The Skate Guy` (0.22), and `Goku` (5.42) sits below `Yggdrasil`
(6.18) — identical to the numbers already recorded in NEXT_STEPS §1 item 5. This is an
instrument/owner-ruling question, not a new code defect — recording as KNOWN, re-verified open,
per the task instructions. No other issues found in this module; it was read in full including
`vector_score`, all five `ANCHORS` entries, and `run()`.

---

## Summary of NEW vs KNOWN

| Finding | File:line | Severity | Status |
|---|---|---|---|
| Truncated-name cache collision (mined feats) | pipeline.py:634-636 | HIGH | NEW |
| write_record drift-merge count-only gate | pipeline.py:518-522 | HIGH | KNOWN, open |
| update_handoff raw os.replace | pipeline.py:1323-1327 | MED | KNOWN, open |
| refused[:5] diagnostic cap | pipeline.py:1744-1747 | MED | NEW |
| evidence/rationale/scale_note truncation, no disclosure | pipeline.py:745-746,1136-1138 | LOW/MED | NEW |
| docstring promises UNREACHABLE, state_of() has 4 states | coverage.py:10-18,82-115 | HIGH | KNOWN, open |
| Truncated-name cache collision (coverage state) | coverage.py:44-46 | HIGH | NEW |
| _so_load swallows all exceptions, comment narrower than code | coverage.py:57-65 | MED | NEW |
| report() diagnostic caps, one with no override | coverage.py:161,171 | MED | NEW |
| Stale hardcoded "of 211" | repass_bands.py:97-98 | MED | NEW |
| Sample-print caps (honestly labeled, low risk) | repass_bands.py:102,108 | LOW | NEW |
| Floor→ceiling invariant violated | anchors.py (whole file) | HIGH | KNOWN, open |
