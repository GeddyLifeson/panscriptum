# AUDIT — batch 02 (sweep #24)

Files in scope and read status:
- `src/pipeline.py` (1875 lines) — read in full, every line.
- `src/grounding.py` (245 lines) — read in full, every line.
- `src/coverage.py` (191 lines) — read in full, every line.
- `src/catalog.py` (127 lines) — read in full, every line.

No source file was edited. `silence.py` and `feats.py` were spot-checked only (grep for `note()`
semantics and to confirm the `_p()` filename scheme matches across modules) — they are not this
batch and were not read line-by-line.

---

## 1. `coverage.py:82-115` — `state_of()` never returns `UNREACHABLE`; a real read exception folds into `NO PAGE`

**MAJOR — VERIFIED**

```
16  NO PAGE      the wiki has no article under this name
17  NO HOST      the source has no wiki at all
18  UNREACHABLE  a host exists but the fetch failed -- the only state that is purely a defect
```
vs.
```
 99            try:
100                with open(fp, encoding="utf-8") as f:
101                    d = json.load(f)
102            except Exception:
103                silence.note("coverage.py:60")
104                continue
105            pages = d.get("pages_read") or d.get("pages") or []
106            feats = d.get("feats") or []
107            st = "CITED" if feats else ("READ" if pages else "NO PAGE")
```

`grep -n "UNREACHABLE" src/coverage.py` returns exactly one hit — the docstring line 18. The
string is never assigned anywhere in the file; `st` can only ever become `"CITED"`, `"READ"`, or
`"NO PAGE"` (line 107), and the function's only other exit is the hard-coded `best = ("NO PAGE",
0, 0)` default at line 87.

Failure scenario: a per-entry evidence file exists (mtime lookup at line 91 succeeds — the entry
was in fact fetched/attempted) but `open()`/`json.load()` at lines 100-101 raises — a torn read
during a concurrent write elsewhere, a transient Windows file-lock (antivirus, indexer), a
truncated file from a killed process, non-UTF-8 bytes. That exception is caught by the bare
`except Exception`, recorded only to `health.py`'s silent-failure ledger via `silence.note`, and
the loop does `continue` — moving to the next `base` (or falling off the loop) with nothing
recorded for this file. The caller sees the untouched `best = ("NO PAGE", 0, 0)`. A transient
defect in the read pipeline is therefore indistinguishable, at every downstream consumer of
`state_of()` (which is all of `measure()`, hence `COVERAGE.json`, the dashboard, and the
published page), from "the wiki genuinely has no article under this name."

This is exactly the distinction the module's own docstring (lines 10-21) says is "the whole
point of the file": *"The distinction between READ and NO PAGE is the whole point of the file.
Collapsing them is what made every silent failure in this project look like an honest absence."*
The docstring both names the defect class and claims a fix (`UNREACHABLE`) that was never
implemented — a comment contradicting its own code (lens item 6), on top of being a swallowed
failure (lens item 2).

---

## 2. `pipeline.py:673` — `rest[:14]` truncates the description-only ceiling-nomination fallback

**MAJOR — VERIFIED**

```
662     rest = sorted((e for e in rec["entries"] if not feats_for.get(e["name"])),
663                   key=lambda e: -len(e.get("description", "")))
...
673     chunks = [with_feats[i:i + 14] for i in range(0, len(with_feats), 14)] or [rest[:14]]
```

Confirmed: for any source with at least one mined-feat entry, `with_feats` is chunked in full
(no entity is excluded — this half of the historical bug, m13, is genuinely fixed, and the
comment block above line 673 accurately describes that fix). But when `with_feats` is empty
(no entity in the source has a mined feat yet — true for any source not yet read, `NO HOST`,
or where the feat miner simply hasn't reached it), the fallback is `rest[:14]`: only the 14
entries with the *longest descriptions* are ever shown to the model for the source's ceiling
nomination. Every other entry — entries 15, 16, ... N by description length — is permanently
invisible to `phase_synthesis` for that pass. This is a live Hard Rule 0 shaped truncation: a
fixed-size slice bounding a universe (the candidate pool for "who is this source's power
ceiling") that should be complete.

The comment at lines 664-672 argues the residual cap is safe because description-only samples
almost always resolve to `unassayed` anyway (99.6% empirically, per the phase-1 comment a few
lines up), since `valid_scale_note` requires a demonstrated feat and a lead paragraph rarely
states one. That reasoning mitigates but does not eliminate the defect: any source whose
strongest entity happens to have a *short* wiki description (a stub) while weaker entities have
long biographical descriptions will never get that entity considered, silently, for as long as
it has no mined feat on file. Contrast this with `grounding.py:143-147`, in the very same
project, which treats *any* nonzero `cap` on an entry list as refusable-by-`SystemExit`
(`"Hard Rule 0 -- rank if you must, never truncate"`) — `pipeline.py` is the file that literally
owns and states that rule, and still ships a silent 14-entry cap on this one path. Inconsistent
enforcement of the project's own headline rule, in the file that is supposed to be the standard.

---

## 3. `pipeline.py:502-530` (`write_record`) — exception during disk-merge falls through and writes the unmerged stale in-memory copy, defeating the function's entire purpose

**MAJOR — VERIFIED**

```
502    merged = rec
503    try:
504        with open(path, encoding="utf-8") as f:
505            disk = json.load(f)
506        if len(disk.get("entries") or []) != len(rec.get("entries") or []):
...
519            merged = disk
...
522    except FileNotFoundError:
523        silence.note("pipeline.py:301")
524        pass
525    except Exception:
526        silence.note("pipeline.py:write_record-merge")
527    tmp = path + ".tmp"
528    with open(tmp, "w", encoding="utf-8") as f:
529        json.dump(merged, f, indent=2, ensure_ascii=False)
530    return _landed(tmp, path)
```

The function's own docstring (lines 488-500) exists specifically to prevent one scenario:
*"Writing the pipeline's stale in-memory copy over that would silently revert twenty-nine
thousand entries, and the loss would read as 'the re-catalogue never ran'."* — and cites a real
incident (marvel.json 1,051 → 30,207 entries). The happy path correctly guards against this:
if the disk copy has drifted, it merges and only ever writes `merged = disk` (the fresher,
larger copy).

But `merged` is initialized to `rec` (the stale in-memory copy) at line 502, *before* the try
block, and the generic `except Exception` at line 525 is reached whenever anything throws
between the successful `open()`/`json.load()` and the assignment `merged = disk` at line 519 —
e.g. a `KeyError`/`TypeError` inside the merge loop, or (more importantly) a `json.JSONDecodeError`
if the on-disk file is truncated or corrupted for any reason external to this atomic-write
pair (a legacy raw writer, a manual edit, a crash during some other tool's non-atomic write —
the docstring at line 418-419 confirms such writers existed historically: *"they were writing
raw, non-atomically, which was its own hazard"*). When that happens, execution falls straight
through to line 527-530 and writes `merged` (still `rec`, the stale copy) over `path` via the
normal atomic rename — i.e. the exact catastrophic overwrite the whole function exists to
prevent, silently, with only a `silence.note` breadcrumb in `health.py`'s ledger that nothing
reads during a normal run.

Concrete scenario: disk copy of some large record is momentarily corrupt/unparseable (any
reason), `write_record` is called mid-phase with the pipeline's smaller in-memory copy, the
`except Exception` swallows the parse error, and the corrupt-but-recoverable larger disk record
is permanently replaced by the smaller stale one. The atomic rename means this is not a torn
write — it is a *complete, successful* write of the wrong content.

---

## 4. `pipeline.py:411-447` (`write_record_catalogue`) — same shape as #3, the catalogue side

**MAJOR — VERIFIED**

```
439    except FileNotFoundError:
440        _ = "silence-exempt: no disk copy yet means nothing to merge; first write"
441        pass
442    except Exception:
443        silence.note("pipeline.py:write_record_catalogue")
444    tmp = path + ".tmp"
445    with open(tmp, "w", encoding="utf-8") as f:
446        json.dump(rec, f, indent=2, ensure_ascii=False)
447    return _landed(tmp, path)
```

Mirrors finding #3 on the catalogue's side of the two-writer contract. If `open(path)`/
`json.load(path)` succeeds but the merge loop that follows (lines ~before 439, iterating
`disk.get("entries")` and copying judged fields onto `rec`'s fresh cast) throws for any reason
other than `FileNotFoundError`, the exception is swallowed and the function proceeds to write
`rec` — the caller's fresh cast — straight over `path`, without the per-entry judgment fields
(bands, scale notes, topics) the merge exists to preserve from the disk copy. The docstring's
own guarantee — *"a merge never shrinks a cast"* — is only true on the exception-free path.
On the exception path it degrades to a plain overwrite: entries survive (rec's list wins either
way per the design), but any judgment data recorded on the disk copy since `rec` was loaded is
silently lost with no signal beyond a `health.py` counter.

Severity note: less catastrophic than #3 (the entry *list* itself is not reverted, since `rec`
here is asserted to be the authoritative fresh cast either way) but still a real, silent loss of
per-entry judgment work (bands/scale_notes/topics) whenever the disk-side merge throws.

---

## 5. `pipeline.py:397-408` (`records()`) — any record file that fails to parse silently vanishes from the entire run, indistinguishable from "not yet catalogued"

**MAJOR — VERIFIED**

```
397  def records():
398      out = []
399      for p in sorted(glob.glob(os.path.join(RECORDS, "*.json"))):
400          try:
401              with open(p, encoding="utf-8") as f:
402                  r = json.load(f)
403          except Exception:
404              silence.note("pipeline.py:191")
405              continue
406          if r.get("entries"):
407              out.append((p, r))
408      return out
```

`records()` is the single enumeration point for every phase in `pipeline.py`, and is imported
and called directly by `coverage.py` (`P.records()`, line 122) and `grounding.py`
(`PL.records()`, line 196). Any record JSON file that exists on disk but fails to parse — for
any reason: corrupted/truncated (see finding #3's scenario), a transient Windows read lock, a
non-UTF-8 byte from a mis-encoded wiki page — is caught by the bare `except Exception`, logged
only to the silent-failure ledger, and the source disappears from `records()`'s return value
entirely for that call. Downstream this is indistinguishable from a source that legitimately
has zero entries or hasn't been catalogued yet: `phase_synthesis`'s `todo` list, `phase_entrypass`'s
`allrecs`, `coverage.measure()`'s per-source rows, and `grounding.main()`'s `out` dict all simply
omit the source, with no record anywhere in their output that a file existed and failed to read.
A whole source (all its entries, all prior synthesis/entrypass work already recorded in that
file) is invisible for the duration of the transient failure, and if the failure coincides with
a phase's "done" bookkeeping being driven off this same enumeration, work already completed for
that source can appear to regress with no diagnostic trail pointing at the actual cause.

---

## 6. `pipeline.py:1293` — `update_handoff` uses bare `os.replace` instead of `silence.replace_retry`

**MINOR — VERIFIED**

```
1289    os.makedirs(os.path.dirname(HANDOFF), exist_ok=True)
1290    tmp = HANDOFF + ".tmp"
1291    with open(tmp, "w", encoding="utf-8") as f:
1292        f.write(md)
1293    os.replace(tmp, HANDOFF)
1294    except Exception:
1295        log("  (handoff update failed: " + traceback.format_exc(limit=1).strip() + ")")
```

Every other tmp+rename pair in this file (`save_state` line ~186, `land_json` line ~482,
`write_record` line ~530, `write_record_catalogue` line ~447) routes the final rename through
`silence.replace_retry`, which — per its own name and per `_landed`'s docstring at line 450-459 —
exists specifically to retry past the transient Windows file-lock/antivirus-scan denials this
project has hit before, and to report back whether the rename actually landed so a caller can
leave work open rather than mark it done. `update_handoff`'s rename is the one exception: a bare
`os.replace()` that, on a transient Windows lock, raises straight into the enclosing
`except Exception` and is logged as a generic "handoff update failed" with no retry — a single
status-file update is skipped for this cycle. Low impact (the file is described in the module
docstring, lines 51-62, as the runner's own machine-written status file, not a two-writer shared
record — the two-writer risk this project actually cares about doesn't apply here), but it is a
straightforward inconsistency with the file's own established atomic-write discipline, in a
project whose signature failure class is exactly "an exception path that quietly does something
different from the happy path."

---

## 7. `coverage.py:141-158` (`report()`) — no zero-entries guard on the aggregate percentages

**MINOR — VERIFIED (edge case only)**

```
141  def report(rows, show=26):
142      n = sum(r["entries"] for r in rows)
...
151      print(f"\n  CITED       {cited:>8,}  {cited/n:>6.1%}   carries a verbatim feat")
```

`measure()`'s per-row `coverage`/`settled` fields are correctly guarded with `max(n, 1)` (line
135-136), but `report()`'s six aggregate percentage lines (151-158) divide directly by the raw
total `n` with no guard. If `rows` is non-empty but every row has `entries == 0` (or `rows` is
empty), `n == 0` and `main()` crashes with `ZeroDivisionError` instead of producing a report.
Only reachable if `measure()` is ever called against a corpus with no catalogued entries at all
— unlikely in the project's current state, but a real, unguarded crash path rather than a
graceful "nothing to report yet."

---

## 8. `coverage.py:44-46` / `pipeline.py:352-353` — duplicated cache-path truncation (`_p`) could theoretically collide two distinct long names

**MINOR — UNVERIFIED (no collision observed; noted for completeness)**

```
coverage.py:44   def _p(base, host, name):
coverage.py:45       return os.path.join(base, re.sub(r"[^A-Za-z0-9]+", "_", host)[:40],
coverage.py:46                           re.sub(r"[^A-Za-z0-9]+", "_", name)[:80] + ".json")
```
```
pipeline.py:352  hd = re.sub(r"[^A-Za-z0-9]+", "_", host)[:40]
pipeline.py:354      nd = re.sub(r"[^A-Za-z0-9]+", "_", e["name"])[:80] + ".json"
```

Confirmed the two implementations use the identical sanitize-then-truncate scheme (40 chars for
host, 80 for name), so they are at least mutually consistent — this is not a divergent-writer
bug. But both truncate to a fixed length before hashing to a filesystem path: two distinct
entity names that share an identical first-80-sanitized-characters prefix (plausible for very
long, near-duplicate wiki article titles — e.g. disambiguation-suffixed names) would silently
alias to the same cache file, with one entity's cached read state overwriting or reporting the
other's. Not observed or reproduced in this audit; flagged as a latent risk given the file's own
described history of exactly this kind of silent-collision defect elsewhere in the project.

---

## Clean / no findings

- **`catalog.py`** — read in full. Read-only query CLI (`stats`/`search`/`address`/`read`
  subcommands); makes no writes to any shared file. The one truncation
  (`missing[:30]`, line 64) is an explicit, announced console-display truncation
  ("... and N more"), not a silent Hard Rule 0 cap — the full count is always printed. No
  correctness bugs, no swallowed failures, no docstring/code contradictions found. The module
  docstring at lines 11-15 itself documents and corrects a previous *documentation* error (a
  URI form nothing ever produced) — a good sign of the file being actively maintained, not a
  code defect.

- **`grounding.py`** — read in full. `classify_source`'s `cap` parameter (lines 120-147) is
  the module's own prior Hard Rule 0 violation, and it is now genuinely fixed: passing any
  non-`None` value raises `SystemExit` with a specific, accurate account of the historical bug
  (Marvel: 153 of 5,012 origin entries read). The write path (`main()`, lines 235-240) uses
  `silence.write_json` correctly. No unguarded truncation, no swallowed-exception-as-empty-result
  pattern found elsewhere in the file. This module is a positive example in the codebase, not a
  finding.

---

## Summary of severities

| # | File:Line | Severity | Status |
|---|---|---|---|
| 1 | coverage.py:82-115 | MAJOR | VERIFIED |
| 2 | pipeline.py:673 | MAJOR | VERIFIED |
| 3 | pipeline.py:502-530 | MAJOR | VERIFIED |
| 4 | pipeline.py:411-447 | MAJOR | VERIFIED |
| 5 | pipeline.py:397-408 | MAJOR | VERIFIED |
| 6 | pipeline.py:1293 | MINOR | VERIFIED |
| 7 | coverage.py:141-158 | MINOR | VERIFIED |
| 8 | coverage.py:44-46 / pipeline.py:352-353 | MINOR | UNVERIFIED |
