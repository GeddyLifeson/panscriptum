# sweep61 batch 15 — audit

Scope: every module below read in full, start to finish, in chunks. No sampling.

  - src/read.py              1691 lines — read in full (2 chunks)
  - src/escalation.py        1445 lines — read in full (2 chunks) [SAFETY-CRITICAL]
  - src/corpus_db.py         1053 lines — read in full (2 chunks)
  - src/gpu_lane.py           684 lines — read in full (1 chunk)
  - src/prose_gate.py         541 lines — read in full (1 chunk) [SAFETY-CRITICAL]
  - src/burgs.py              442 lines — read in full (1 chunk)
  - src/catalogue_models.py   364 lines — read in full (1 chunk)
  - src/tempus.py             297 lines — read in full (1 chunk)

Total: 6,517 lines across 8 modules.

## Context

All eight modules are heavily self-documented with dense, numbered "order" comments recording
past defects and their fixes (many spanning sweeps 22–59). This is a mature, extensively
audited codebase; most of the shapes this brief's priority list asks about (tautologies,
fail-open guards, caps/truncations, dead code) are already named and handled in the code's own
comments, with cross-references to the drill/verify_math nets that pin them. I did not
re-report any of those. What follows is the residue after that filtering.

## Findings

### 1. VERIFIED — real bug (not fail-open; over-refusal direction) — `src/prose_gate.py`, `unearned_instrument()`

```python
def unearned_instrument(text, cited_names):
    ...
    for b in _entry_blocks(text):
        head = b.splitlines()[0] if b.splitlines() else ""
        name = head.strip().strip("*").strip()
        if not _AXIS_RE.search(b):
            continue
        base = re.sub(r"\s*\(.*", "", name).strip()
        if name not in cited_names and base not in cited_names:
            out.append(name or "(unnamed entry)")
```

`name` is derived by stripping only `*` characters off the entry's first line. Every other
label-matching regex in this same file (`_CLASS_LINE`, `_AXIS_RE`, `_AXIS_LABEL`,
`_INSTRUMENT_MARK`) explicitly tolerates the fuller decoration set the model is documented
elsewhere in this file to emit: `[\s*_#>-]*` (whitespace, asterisk, underscore, hash,
blockquote marker, dash). `unearned_instrument`'s name line does not use that set — it only
handles `**Bold Name**`-style wrapping, not a markdown heading (`### Name`), an underscore
italic (`_Name_`), or a blockquote-style entity line (`> Name`).

Verified by running the function directly:

```
head.strip().strip("*").strip() on "**Some Entity**" -> "Some Entity"   (matches cited_names)
head.strip().strip("*").strip() on "### Some Entity"  -> "### Some Entity"  (does NOT match)
```

Live repro:
```python
import sys; sys.path.insert(0, 'src'); import prose_gate as PG
text = "◈ ### Some Entity\nShelfmark: X\nClass: Person\nMagnitude: M4\nThreads: pending\n" \
       "Wisdom: 28 (Transcendent, Grade III)\n"
PG.unearned_instrument(text, {"Some Entity"})
# -> ['### Some Entity']   (should be [], the entity IS cited)
```

Effect: a genuinely-cited entity whose name line the model decorated as a markdown heading (or
underscore/blockquote) is reported as "unearned instrument" and the block is refused by
`generate.py`'s `_unearned` check, even though the axis score is properly earned. This is a
false positive, not a false negative — the gate over-refuses rather than under-refuses, so it
does not weaken Hard Rule 3 (fail-closed is preserved; if anything it fails MORE closed than
intended). Reported as a real bug per the brief's priority 4, not as a safety hole. `drill.py`
and `verify_math.py`'s existing nets for this function (`drill.py:2343-2364`,
`verify_math.py:7332-7338`) cover the "no decoration" and "bold" cases only (`**Athuri**`,
`**Wisdom:**`, `**Strength**:`) — none exercise a heading/underscore/blockquote-decorated name
line, so this gap is unproven in either direction, which is itself worth flagging under
standing lesson 9 ("a guard nobody has watched refuse is a guard that has never run") — except
here it's the inverse: a false-refusal path nobody has watched NOT fire.

### Everything else — no new VERIFIED or SUSPECTED findings

I read `escalation.py` and `prose_gate.py` in full given their safety-critical status and did
not find any tautological check, fail-open guard, or false doc/comment in either beyond what
their own comments already record as fixed. `escalation.py`'s halt/stop machinery (CAS loops,
`_halt_lock`'s deliberate fail-open, the OWNER-only `clear()`/`resume_subsystem_verdict()`
person-checks, `_a_probe_release`'s fail-closed-on-import-failure) all check out against their
own stated invariants when traced by hand.

`gpu_lane.py`'s Windows `_alive()` PID check, lease/heartbeat/staleness logic, and the
documented fail-open contract all hold up; no path returns "alive" where "unknown" is claimed
or vice versa.

`corpus_db.py`'s three-state sentinels (`SPINE_LOOKUP_FAILED`, `HOST_LOOKUP_FAILED`, the
`unavailable`/`compared` deletion-check tri-state) are internally consistent, and the
`worst_cited`/`below_floor_cited` canned queries correctly avoid the `entries=0` NULL-sort
failure mode their own comments describe having been bitten by before.

`burgs.py`'s `class_histogram`/`_rank_at_or_above` contiguous-block arithmetic was traced by
hand against `CLASSES` and produces correct non-overlapping counts; the `--limit` narrowing
logic (`min(int(limit), n)`, `max(0, ...)`) cannot invent or silently drop settlements.

`catalogue_models.py`'s `LISTED`/`EMPTY_LIST`/`UNREACHABLE`/`UNCONFIGURED` four-state outcome
model is exhaustively handled at every read site (`live`, `verified`, `unverified`, the
`stale` computation) with no state falling through a truthiness check.

`tempus.py` is small and mostly declarative (band-edge-derived bit costs); the one place I'd
flag as worth a second pair of eyes but could not verify without reading `assay.py` (out of
this batch's scope) is `band_resolution()`'s `LADDER.index(band)` call, which is guarded by
`if band not in BAND_EDGES` but not by `band not in LADDER` — if the two ever have different
keysets this would raise uncaught. QUESTION, not a finding: I have not read `assay.py` to know
whether `BAND_EDGES` and `LADDER` are guaranteed to share a keyset by construction.

## Summary of findings by kind

- Tautologies / checks that cannot fail: 0
- Fail-open guards (unintended): 0
- Caps/truncations hiding data: 0
- Real bugs: 1 (VERIFIED — `prose_gate.unearned_instrument` markdown-decoration name-matching
  gap, over-refusal direction)
- False comments/docstrings: 0
- Dead code: 0 (beyond what the code's own "REPORTED DEAD, NOT DELETED" markers already record)
- Questions (possible deliberate design, unverified): 1 (`tempus.band_resolution` LADDER/
  BAND_EDGES keyset assumption, out of batch scope to verify)
