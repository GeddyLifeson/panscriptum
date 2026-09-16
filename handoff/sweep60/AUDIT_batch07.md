# sweep60 batch 07 audit

Modules read in full, uncapped, no sampling:

- src/standards.py (2477 lines)
- src/rigor.py (1132 lines)
- src/wiki_source.py (808 lines)
- src/withdraw_chapters.py (614 lines)
- src/backfill.py (494 lines)
- src/retry_synthesis.py (379 lines)
- src/catalogue_aurora.py (328 lines)
- src/cachekey.py (217 lines)
- src/module_index.py (192 lines)

Total 6,641 lines, all read top to bottom. No file in this batch was edited.

## Overall impression

This batch is unusually heavily self-audited already. Nearly every one of these nine modules
carries its own multi-paragraph docstrings and inline comments recording a *previous* instance of
exactly the failure classes this sweep is asked to hunt for -- tautological checks, fail-open
guards, silent caps, stale line citations, green-by-absence -- each with the fix already landed
and the reasoning for the fix spelled out (often citing an order id, a run number, and a measured
count). `cachekey.py`'s whole docstring, `catalogue_aurora.slug()`, `backfill.roster()`,
`wiki_source.all_categories()`/`category_members()`, and roughly two-thirds of `standards.py`'s
`check()` are each, in effect, a worked example of the sweep's own finding categories being
caught and closed by an earlier pass. I read every one of these histories rather than trusting
the docstring's claim, and where I could cheaply verify the current code actually matches what
the comment says was fixed (see below), it did.

I did **not** find a new instance of finding-category 1 (a check that cannot fail) in live code
in this batch. I verified this concretely in two places that looked like candidates at a glance:

- `src/rigor.py` `_strongly_connected` (Tarjan SCC used by `bradley_terry`'s Ford's-condition
  check): I ran it standalone against three synthetic graphs (a 3-cycle + isolated node, two
  disjoint 2-cycles, and an acyclic chain) and it returned the correct component partition in all
  three, so the "is the comparison graph connected" gate it feeds is not vacuous.
- `src/module_index.py`'s duplicate-group-name and stale-group-name self-checks: traced through by
  hand; both compare against real, independently-derived data (`_modules()`'s disk walk vs.
  `GROUPS`'s hand-kept list), not against a value computed from the same list being checked.

## Findings

I have two low-confidence items, both UNSURE (flagged as such, not presented as confirmed bugs),
and no HIGH or MEDIUM confidence findings from this batch.

### 1. UNSURE -- possible false-positive in the "unanswered records" head-read, `src/standards.py:1291-1296`

```python
_readfeats = os.path.join(HERE, "data", "readfeats")
if not os.path.isdir(_readfeats):
    raise FileNotFoundError(_readfeats)
unans_files = 0
for fp in _g.glob(os.path.join(_readfeats, "**", "*.json"), recursive=True):
    with open(fp, encoding="utf-8") as f:
        head = f.read(700)
    if '"chunks_unanswered": 0' not in head and "chunks_unanswered" in head:
        unans_files += 1
    elif "chunks_unanswered" not in head:
        unans_files += 1          # written before the guard existed
```

This reads only the first 700 bytes of each cached record and looks for the literal substring
`"chunks_unanswered": 0`. If a record's JSON serialisation happens to place the
`"chunks_unanswered"` key close enough to the 700-byte boundary that the key name is inside the
first 700 bytes but its value is not (e.g. long field values earlier in the object push the key
past ~680 bytes), the first `if` is satisfied (`'"chunks_unanswered": 0'` is absent because it's
truncated, and `"chunks_unanswered"` is present) and the file is counted as `unans_files += 1`
even when the real value on disk is `0` (fully read). That would report a HIGH-severity "evidence
integrity" standard as breached over records that are actually fine.

I have **not** verified whether `chunks_unanswered` is written early enough in these records'
JSON serialisation to make this unreachable in practice (I did not find a writer for
`data/readfeats/*.json` in this batch's files, so I could not check the field's typical byte
offset). This is exactly the same shape of bug (`m6`-adjacent: a cut landing on the one field a
check depends on) that this same file explicitly fixed at least three other times elsewhere
(the `[:40]`, `[:120]`, `[:28]`/`resident[0]` fixes documented around lines 736, 1596, 1999) -- so
if the offset assumption ever stops holding (a record gains a new long field before
`chunks_unanswered`), this reproduces the same class of defect the surrounding code was written
to eliminate. Flagging as unsure rather than confirmed because I could not establish the actual
byte offset of the field in a real `data/readfeats/*.json` file.

### 2. UNSURE -- possible false collision from unset `address` fields, `src/standards.py:1381-1398`

```python
with open(os.path.join(HERE, "data", "SHELFMARKS.json"), encoding="utf-8") as f:
    marks = json.load(f)
addrs = [v.get("address") for v in marks.values() if isinstance(v, dict)]
collisions = len(addrs) - len(set(addrs))
```

`v.get("address")` returns `None` for any record dict that lacks an `"address"` key. If two or
more such records exist, they all collapse to the single `None` value in `set(addrs)`, and
`collisions` would count them as address collisions even though neither has been assigned a real
address at all -- i.e. "no address yet" would misreport as "two worlds sharing one address",
against a `MAX_SHELFMARK_COLLISIONS = 0` HIGH-severity floor.

I checked this against the one writer of `data/SHELFMARKS.json` I could find in this pass
(`src/pipeline.py:2822`, `marks[desig] = {"address": addr, ...}`), which always sets `"address"`
to a real value when it writes a record, and that same module computes its own duplicate count as
`len(marks) - len({v["address"] for v in marks.values()})` using bracket access (which would raise
`KeyError` rather than silently coalescing to `None` if the key were ever missing). So in the
common case this is not reachable -- the two writers I could see are consistent with every record
always carrying a real address. I flag it only because `standards.py`'s version uses `.get()`
with an implicit `None` default rather than requiring the key, so if some other, unaudited writer
ever appended a partial record to this file (or the file were manually edited), the false-
collision reading would follow silently, and I could not rule that out for certain without
reading `address_space.py` (out of this batch's assignment) in full.

## Explicitly checked and found NOT to be current bugs

- `src/backfill.py` `main()`: `recs = P.records()` is reused across `audit()` and
  `backfill_source()` calls in the `--all` path. I checked `pipeline.records()` and confirmed it
  materialises a list (`out = []; ...; return out`), not a generator, so this is safe -- an
  earlier version of my read flagged this as a possible "iterator exhausted by first consumer"
  bug and it is not one.
- `src/withdraw_chapters.py` `_land_merged`'s early `break` when `silence.digest_of(path) == seen`
  after a failed compare-and-swap: read closely: it is deliberate (a denial while the file is
  provably unchanged is treated as a real refusal to report rather than retried blindly), not a
  short-circuit that silently drops a legitimate retry.
- `src/rigor.py` `bradley_terry`'s two-refusal `if`/`elif`-turned-independent-`if` block: verified
  by re-derivation that `identified=True` mathematically implies both `undefeated` and `winless`
  are empty for n>1 (an in-degree-0 or out-degree-0 node cannot be in a single all-spanning SCC),
  so the current code (checking both independently rather than chaining) is correct and not a
  case of a check that cannot fail -- it is two checks that CAN each independently fail, correctly
  un-chained.
- `src/module_index.py` `main()`'s duplicate-group and stale-group checks are cosmetic-severity
  (exit 1, well-labelled) rather than silently absorbed; verified the exit code path is reached in
  both cases.

## Coverage note

All 9 files were read in full via direct file access (not summarised, not sampled), confirmed by
line counts matching `wc -l` before reading. No file under `src/` was modified. Nothing was run
from `C:\Users\imarl\panscriptum-export`. `sweep_plan.record` for sweep60 batch 7 is called
separately per the task instructions, after this report was written.
