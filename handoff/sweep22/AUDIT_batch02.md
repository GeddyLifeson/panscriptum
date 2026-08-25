# Batch 02 audit — pipeline.py, burgs.py, halo.py, scale_theories.py

Every line of all four files was read top to bottom. `pipeline.py` was given the deepest pass
per the assignment note (it owns the two-writer contract).

---

## HIGH

### H1. `phase_synthesis`'s description-only fallback caps a source's roster to 14 entries — Hard Rule 0

**pipeline.py:662-673**, VERIFIED

```python
with_feats = [e for e in rec["entries"] if feats_for.get(e["name"])]
with_feats.sort(key=lambda e: -len(feats_for[e["name"]]))
rest = sorted((e for e in rec["entries"] if not feats_for.get(e["name"])),
              key=lambda e: -len(e.get("description", "")))
...
chunks = [with_feats[i:i + 14] for i in range(0, len(with_feats), 14)] or [rest[:14]]
```

When a source has **zero** feat-mined entries yet (the documented common case — `_mined_feats`
says explicitly "this improves on its own as `read.py` works through the roll", i.e. most
sources start with an empty `feats_for`), `chunks` falls back to a **single** `rest[:14]` —
the 14 entries with the longest descriptions, out of however many the source actually has.
Every other entry in that source's cast is never shown to the model for ceiling nomination,
ever, for as long as `feats_for` stays empty.

The in-line comment argues this is deliberate: "The description-only fallback stays a single
ranked chunk deliberately: a lead paragraph cannot carry a ceiling feat." That is the same
reasoning shape Hard Rule 0 explicitly rules out in `CLAUDE.md`: *"Ranking is still allowed and
is encouraged... **Ranking then truncating is not**."* Here the code does exactly that: sorts
`rest` by description length, then slices the top 14 and discards the rest of the roster. The
sibling code path for feat-bearing entries (the very same block, one paragraph up) was already
corrected under this exact rule (comment cites "BUGS m13, Hard-Rule-0-shaped, ruled by the owner
2026-08-24: FIX IT ALL") — chunking through **every** feat-bearing entry rather than sampling
14 — but the fallback branch kept the old fixed-sample-of-14 behaviour for exactly the sources
where it matters most (nothing has been feat-mined for them yet).

**Repair sketch**: chunk through all of `rest` the same way `with_feats` is now chunked
(`[rest[i:i+14] for i in range(0, len(rest), 14)]`), accepting the extra call cost the owner
already accepted for the feat-bearing path, or explicitly get the owner's sign-off that
description-only chunks are exempt (in which case the code comment should say "owner-approved
exemption," not read as though the Hard Rule 0 fix already covers this branch).

---

### H2. `write_record`'s drift check is length-only — a same-count concurrent write is silently discarded

**pipeline.py:487-530**, VERIFIED

```python
merged = rec
try:
    with open(path, encoding="utf-8") as f:
        disk = json.load(f)
    if len(disk.get("entries") or []) != len(rec.get("entries") or []):
        by_name = {e.get("name"): e for e in rec.get("entries") or []}
        for de in disk.get("entries") or []:
            se = by_name.get(de.get("name"))
            if not se:
                continue
            for fld in (...):
                if fld in se:
                    de[fld] = se[fld]
        for key, val in rec.items():
            if key != "entries":
                disk[key] = val
        merged = disk
        log(f"    write_record: ... merged")
except FileNotFoundError:
    ...
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)
return _landed(tmp, path)
```

The docstring says this exists precisely because "the catalogue and the pipeline both write
these files... marvel.json went from 1,051 entries to 30,207 in one such pass," and merges
*only when the entry count differs*. But the file's own `phase_entrypass` comments (the
`entry_settled`/`batch_settled` block, ~line 963) describe a **second, real, concurrent writer**
that does *not* change entry count: `cleanup.py` "strikes wiki-navigation cruft... by setting
`catalogued = False` and writing an `excluded` reason" on **existing** entries — no add, no
remove. If `cleanup.py` (or anything else) mutates a record's existing entries in place while
`phase_entrypass` holds a long-lived, now-stale in-memory copy of the same record (`phase_write`'s
own docstring calls entrypass "Multi-day"), the length check sees no drift, so `merged = rec`
runs unconditionally — the entire stale in-memory copy is written straight over disk, silently
discarding whatever the concurrent writer changed. This is the exact defect class this module's
own comments describe paying for repeatedly ("Cleanup's entire effect on the corpus had been
undone"), reintroduced one layer down, in the persistence function itself rather than in the
resume-gate logic that was already fixed.

The project's own handoff table (pipeline.py ~1290) explicitly says `cleanup.py` "run[s]
standalone and do[es] not block the sweep" — i.e. concurrent execution with the pipeline is the
intended operating mode, not a misuse case.

**Repair sketch**: merge on drift whenever *any* field on *any* matching entry differs, not just
on a length mismatch — or take a lock / mtime-check before the fast path.

---

### H3. Neither merge function preserves `excluded`, and `write_record`'s merge can silently flip a disk `catalogued: False` back to `True`

**pipeline.py:434-438** (`write_record_catalogue`) and **pipeline.py:512-515** (`write_record`),
VERIFIED

```python
# write_record_catalogue
for fld in ("category", "scale_note", "scale_note_rejected",
            "magnitude", "topic", "catalogued"):
    dv, sv = de.get(fld), se.get(fld)
    if dv and (not sv or sv == "unassayed"):
        se[fld] = dv
```
```python
# write_record
for fld in ("category", "scale_note", "scale_note_rejected",
            "magnitude", "topic", "catalogued"):
    if fld in se:
        de[fld] = se[fld]
```

Both hard-coded field lists omit `excluded`, the exact key `cleanup.py` uses (per the
`batch_settled` docstring a few hundred lines below) to mark a struck entry. So even when the
*count-drift* merge path in H2 above does run:

- `write_record_catalogue`'s guard `if dv and (...)` additionally requires the disk value to be
  *truthy* — so a disk `catalogued: False` (`dv = False`) never overwrites the fresh cast's
  value at all, and `excluded` is never copied in either direction.
- `write_record`'s merge copies `se["catalogued"]` (the pipeline's own in-memory value, which
  entrypass sets to `True` unconditionally for anything it judges) onto `de["catalogued"]`
  whenever the key merely exists — with no truthiness check — so a disk-side `catalogued: False`
  set by `cleanup.py` gets overwritten back to `True` by the very merge that was supposed to
  protect concurrent writers. `de["excluded"]` itself survives untouched (it's simply never
  touched), leaving the merged record in a self-contradictory state: `excluded: "<reason>"` next
  to `catalogued: True`.

This is the same "149 entries... Cleanup's entire effect on the corpus had been undone" failure
the surrounding comments describe fixing at the resume-gate level (`entry_settled`,
`batch_settled`), reappearing at the persistence layer that both fixes ultimately write through.

**Repair sketch**: add `"excluded"` to both field lists, and drop the truthy-only guard in
`write_record_catalogue` (or add an explicit `False`-is-meaningful case) so a disk-side
`catalogued: False` can never be silently promoted back to `True` by a merge.

---

## MEDIUM

### M1. `update_handoff` writes its status file via raw `os.replace`, not `silence.replace_retry`

**pipeline.py:1290-1295**, VERIFIED

```python
os.makedirs(os.path.dirname(HANDOFF), exist_ok=True)
tmp = HANDOFF + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    f.write(md)
os.replace(tmp, HANDOFF)
except Exception:
    log("  (handoff update failed: " + traceback.format_exc(limit=1).strip() + ")")
```

Every other atomic write in this file (`save_state`, `write_record`, `write_record_catalogue`,
`land_json`, via `_landed`) goes through `silence.replace_retry`, whose own docstring explains
exactly why: "on Windows the rename is DENIED while any reader holds the target open... this
project's state files all have readers on their own clocks (the dashboard polls records...)."
`handoff/RUN_STATUS.md` is that same kind of file — machine-rewritten "after every completed
unit," readable by the owner or a dashboard at any moment — yet it uses a bare `os.replace`
wrapped only in a broad `except Exception` that logs and moves on. The failure isn't silent (it
is logged), but it doesn't get the retry-then-succeed behaviour the rest of the file was built to
guarantee, and a transient reader collision here means that round's status update is simply lost
rather than retried.

**Repair sketch**: `silence.replace_retry(tmp, HANDOFF)`, matching every other writer in the file.

### M2. `burgs.py --write`'s own print message contradicts what the code does

**burgs.py:186-230**, VERIFIED

```python
worlds = WS.build_all()          # every world; Hard Rule 0
...
per_world[w["designation"]] = bs        # built for every world in `worlds`, uncapped
...
if args.write:
    p = os.path.join(HERE, "data", "BURGS_SAMPLE.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(per_world, f, indent=2, ensure_ascii=False)   # every world; Hard Rule 0
    print(f"\nwrote {p} (sample of 50 worlds; the rest regenerate on demand)")
```

`WS.build_all()` is called with no `limit` (confirmed in `worldseed.py:244`, `def
build_all(limit=None)`), so `worlds` — and therefore `per_world`, and therefore
`BURGS_SAMPLE.json` — actually holds **every** world, exactly as the code comments say. The
printed message claiming it's "a sample of 50 worlds" is simply stale/wrong. This is not itself
a Hard Rule 0 violation (the data written is genuinely the full set), but it is a comment/output
string flatly contradicting the code around it, and in a project this alert to "a cap does not
fail, it returns a smaller universe wearing the same shape as the real one," a stale message that
describes full data as a sample is exactly the kind of thing that invites a future edit to
"restore" the (never-real) 50-world cap.

**Repair sketch**: fix the print string, or cite the true count (`len(worlds)`).

### M3. `burgs.py` and `halo.py` write `data/` files with a bare non-atomic `open(path, "w")`

**burgs.py:226-229**, **halo.py:170-171**, VERIFIED

```python
# burgs.py
with open(p, "w", encoding="utf-8") as f:
    json.dump(per_world, f, indent=2, ensure_ascii=False)
```
```python
# halo.py
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
```

Both write directly to their target path in `data/` with no temp-file-plus-rename and no
`silence.replace_retry` — the exact pattern `pipeline.py`'s own `land_json`/`_landed` exist to
replace ("the later phases wrote their artifacts as `json.dump(obj, open(path, "w"), ...)`: not
atomic... several of these are read by a LATER PHASE"). `BURGS_SAMPLE.json` and
`HALO_ASSAYS.json` are both standalone-tool outputs rather than files a phase reads mid-run, so
the blast radius is smaller than the phase artifacts `land_json` was written for — but a crash or
a reader (e.g. the dashboard, or another tool) opening either file mid-write will see a truncated
or invalid JSON file, with no atomicity guarantee at all.

**Repair sketch**: route both through `pipeline.land_json` (already imported transitively via
`worldseed`/`address_space` in `burgs.py`; `halo.py` would need the import) or replicate the
tmp+`silence.replace_retry` pattern locally.

### M4. `write_record` / `write_record_catalogue` collapse duplicate entry names via dict construction

**pipeline.py:426, 507**, VERIFIED (code-level; real-world duplicate names not confirmed)

```python
by = {e.get("name"): e for e in rec.get("entries") or [] if isinstance(e, dict)}   # write_record_catalogue
...
by_name = {e.get("name"): e for e in rec.get("entries") or []}                     # write_record
```

If a source's entry list ever legitimately contains two entries sharing the same `name` (e.g.
two distinct attestations catalogued under an identical string before weave/resolution runs),
the dict comprehension keeps only the last one encountered; the other is invisible to the merge
logic and, depending on which side (disk vs rec) it survives on, may or may not make it into the
final written file. Every downstream lookup that treats `name` as unique (`by_name.get(...)`,
`key = "%s::%s" % (src, e.get("name"))` in `phase_shelve`, etc.) inherits the same assumption, so
this isn't a new failure mode this batch introduces — but it sits directly inside the two
functions the sweep was told to scrutinise hardest, so it's flagged here rather than assumed safe.

---

## LOW

### L1. `scale_theories.py`: five physical constants declared, never used — dead code

**scale_theories.py:23-27**, VERIFIED

```python
C_LIGHT = 2.99792458e8
G_NEWTON = 6.67430e-11
HBAR = 1.054571817e-34
NUCLEAR_DENSITY = 2.3e17
PLANCK_LENGTH = 1.616255e-35
```

None of `C_LIGHT`, `G_NEWTON`, `HBAR`, `NUCLEAR_DENSITY`, or `PLANCK_LENGTH` is referenced
anywhere else in the file (confirmed by grep), and the only other file that mentions
`scale_theories` (`derivation.py:477`) references it only as a bare string in a module-name list,
not an import. The numeric values these constants represent (e.g. `2.3e17` for nuclear density,
`6.3e18 J` for `m*c^2` at 70 kg) are hand-computed and hardcoded as prose directly into the
`THEORIES` dict's `"physics"` strings instead. Harmless, but dead.

### L2. `burgs.py`: `HAMLET_FLOOR` (40) vs. the hardcoded population clamp (30) disagree

**burgs.py:85-109** vs **burgs.py:148**, VERIFIED

`burg_count` derives the roster size `n` from `HAMLET_FLOOR = 40` — "the rule already knows
where to stop: it runs until a settlement falls below the floor" — but `burgs_for`'s per-rank
population is computed as `pop = max(30, int(p1 / (k ** ZIPF_Q)))`, clamping the smallest
settlements to a floor of **30**, not 40. Because `burg_count`'s condition `factor` (e.g.
`"thriving": 1.15`) is applied *after* `n` is derived from the 40-floor, the extra ranks it adds
land below 40 and get silently clamped to 30 instead of being excluded — a settlement the
module's own comment calls "the smallest thing the record still calls a burg" (the 40 floor) can
end up in the roster at population 30. Cosmetic/minor: it slightly pads the tail of the roster
rather than truncating it, so it's not a Hard Rule 0 concern, just an internal inconsistency
between the two numbers.

### L3. `pipeline.py` / `halo.py`: `_BAD_CHARS` self-scan leaves its file handle unclosed

**pipeline.py:85**, **halo.py:37**, VERIFIED (style only; no observed impact)

```python
if any(c in open(os.path.abspath(__file__), encoding='utf-8').read() for c in _BAD_CHARS):
```

`open(...)` here is never given a `with` block or closed explicitly; CPython's refcounting closes
it immediately after `.read()` returns since the file object isn't retained, so there's no
practical leak on CPython — but it's the one `open()` call in either file that doesn't follow the
project's otherwise consistent context-manager discipline, and would leak under PyPy or any
non-refcounting interpreter.

### L4. `pipeline.py`: several `silence.note()` tags carry stale line numbers

**pipeline.py:403, 594, 611, 522** (tags read `"pipeline.py:191"`, `"pipeline.py:261"`,
`"pipeline.py:277"`, `"pipeline.py:301"`), VERIFIED, cosmetic only

The tag strings passed to `silence.note()` at these call sites don't match their current line
numbers (the file has clearly grown since they were written). These are just identifying labels
for the failure ledger, not runtime file:line references, so nothing breaks — but a maintainer
grepping the ledger for `pipeline.py:191` to find the call site would land on the wrong line.

---

## Per-module verdicts

- **pipeline.py**: 3 HIGH, 2 MEDIUM, 2 LOW (L3/L4 above; L1/L2 belong to the other files). Not
  clean — the two-writer contract functions (`write_record`, `write_record_catalogue`) have a
  real residual gap against same-count concurrent edits, and `phase_synthesis`'s fallback branch
  has a live Hard Rule 0 exposure.
- **burgs.py**: 0 HIGH, 2 MEDIUM, 1 LOW. The rank-size math itself is sound and genuinely
  uncapped in its real call path (`limit=` is only ever exercised by `verify_math.py` as a
  measurement bound, a legitimate judgment call, not a violation).
- **halo.py**: 0 HIGH, 1 MEDIUM (shared with M3 above), 1 LOW (shared with L3 above). The
  hand-scored four-entity `ROSTER` is a deliberate worked Custodial Assay, not a truncated
  cataloguing roster — no Hard Rule 0 concern there. Otherwise clean.
- **scale_theories.py**: CLEAN. No I/O, no roster, no caps, no exception handling to swallow
  anything, no correctness bugs found. Only finding is the L1 dead-code note.
