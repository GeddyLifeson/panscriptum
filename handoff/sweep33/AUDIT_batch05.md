# Batch 05 — run33
Modules read: drill.py (1299 lines), gpu_lane.py (480 lines), address_space.py (347 lines),
weave_index.py (277 lines), burgs.py (236 lines), snapshot.py (176 lines),
compress_store.py (66 lines)

## FINDINGS

### 1. drill.py:1036-1038 — a net that cannot fail (the exact defect this batch was told to hunt for)  [severity: MAJOR]
`drill_fetch()`'s "a refused page is RECORDED, not dropped" net:
```python
net(a, "a refused page is RECORDED, not dropped",
    lambda: "pages_refused" in F.evidence_for.__doc__ or True,
    "the distinction between 'no evidence' and 'we were blocked' must survive to the cache")
```
`X or True` is always `True` once the left side evaluates without raising — the net passes
whether or not `"pages_refused"` is in the docstring, whether or not `feats.evidence_for`
actually records refused pages anywhere, and would keep passing even if the entire
refused-page-tracking feature were deleted outright (as long as `evidence_for.__doc__` stays
non-`None`, which it will). This is precisely "a net that attacks a guard in a way the guard
would pass even if it were deleted." Fix: assert on real behaviour of `evidence_for` (or
whatever function actually threads `pages_refused` through), not a docstring substring ORed
with a constant.

### 2. drill.py:1039-1041 — a net that checks a threshold and an attribute, not the behaviour it names  [severity: MINOR]
```python
net(a, "persistent throttling hands off to quarantine rather than hammering",
    lambda: F.THROTTLE_STRIKES >= 1 and hasattr(F, "note_throttled"),
    "past a few strikes, 'busy' is a less likely reading than 'blocked'")
```
This never drives a call through the throttle-to-quarantine path; it checks that a constant is
at least 1 and that a function with a plausible name exists. Renaming or gutting the actual
hand-off logic inside `note_throttled` (as opposed to the sibling `_backoff_adapts()` net two
lines up, which does call `note_throttled`/`note_ok` and inspect `_BACKOFF`) would not be
caught by this net at all. Weaker sibling of #1, not fully tautological but not testing what
its name claims either.

### 3. drill.py:922-931 (drill_snapshot) — the one snapshot net never exercises a directory, which is exactly where the live bug in snapshot.py hides  [severity: MINOR]
`SNAP.before("drill", ["config.yaml"], ...)` snapshots a single **file**. `snapshot.verify()`'s
directory path (see finding #6 below) is never touched by any net in this battery, so the drill
would report every net HELD even with the directory-verification gap present — which it
currently is.

### 4. address_space.py:171-183 — `shelfmark()`'s docstring describes behaviour the code no longer has  [severity: MAJOR]
```python
def shelfmark(addr):
    """The charter's own notation. H and X print as '?' because they are uncharted.
    ...
    """
    f = unpack(addr)
    return (f"Ω › H{f['hyperverse']} › X{f['xenoverse']} › Mt.{f['metaverse']} › "
            f"Mv.{f['multiverse']} › U-{f['universe']} › G.{f['galaxy']:x} › P.{f['planet']}")
```
The docstring says H and X print as `'?'`. The code prints real integers for both
(`H{f['hyperverse']}`, `X{f['xenoverse']}`) — confirmed by reading the format string directly.
The inline comment just above the `return` even says why ("printed '?' through two earlier
passes ... Neither is true any more"), so this looks like an intentional, considered change to
the *code* whose docstring simply never got updated to match. Given CLAUDE.md's Hard Rule 4
("Don't invent Shelfmarks... requires real classification research per entity that hasn't been
done"), anyone reading only the docstring would believe this module is still emitting the honest
placeholder when it is not — worth the owner's explicit sign-off that H/X are now real charted
values project-wide, not just a self-consistent module. (Reproduces sweep30/AUDIT_batch05.md
§4.1, still unfixed.)

### 5. address_space.py:26-27 vs. FIELDS (130-139) — module-header bit-width table is stale  [severity: MINOR]
The header docstring's derivation table describes a 5-field, 74-bit/10-byte address
(`hyperverse|universe|galaxy|star|planet`). The actual `FIELDS` list has grown to 8 entries
(`hyperverse, xenoverse, metaverse, multiverse, universe, galaxy, star, planet`), and
`TOTAL_BITS` is computed from all 8 — a different total than the header claims. Docs-only, but
it is the module's own advertised justification for its design and it no longer matches the
design. (Reproduces sweep30/AUDIT_batch05.md §4.2, still unfixed.)

### 6. address_space.py:264-278 (`main()`) — `zip(FIELDS, srcs)` silently drops 3 of 8 rows and mislabels the rest  [severity: MINOR]
```python
srcs = ["weave.py: 8 divisions breaks the six-degree diameter",
        "168 continuities resolved by the weave",
        "Lauer et al. 2021 (New Horizons LORRI)",
        "dwarf-dominated mean stars per galaxy",
        "Cassan et al. 2012, Nature"]
for (name, n), s in zip(FIELDS, srcs):
    print(f"{name:<14}{n:>14.3e}{WIDTHS[name]:>7}   {s}")
```
`srcs` has 5 entries, left over from the old 5-field scheme; `FIELDS` now has 8. `zip` silently
stops after 5 pairs, so the printed derivation table (a) never shows `galaxy`, `star`, or
`planet` at all, and (b) pairs `xenoverse`, `metaverse`, `multiverse`, `universe` with citation
strings that were written for `universe`, `galaxy`, `star`, `planet` respectively — e.g. the row
labelled `xenoverse` prints the citation "168 continuities resolved by the weave," which is the
citation for `universe`, not `xenoverse`. Anyone reading `python src/address_space.py`'s console
report gets a wrong and incomplete table. Not data-affecting (the real `WIDTHS`/`CAPACITY` math
uses all 8 fields correctly), but the report is wrong.

### 7. address_space.py:206 — `citation_card()`'s decimal formatting has no upper clamp  [severity: MINOR — currently dead code, see #8]
```python
f"𝔄 {band}" + (f".{int(round(decimal*100)):02d}" if decimal is not None else "")
```
`decimal=0.996` → `round(99.6)` → `100` → formatted with `:02d` as `"100"` (three digits), giving
a malformed `"𝔄 M4.100"` instead of a two-digit decimal. Confirmed by reading the format
expression directly — nothing clamps `decimal` below 1.0 first. Currently unreachable in
production because `citation_card()` has zero callers (finding #8), but it would misfire the
moment anything calls it with a decimal ≥ 0.995. (Reproduces sweep29/30 findings, still unfixed.)

### 8. address_space.py:186, 216 — `citation_card()` and `seed_from_card()` are dead code  [severity: MINOR]
Grepped the whole repo (`src/`, `handoff/`, `docs/`, `reference/`): no caller anywhere except
their own definitions. `map_seed()` — the function `seed_from_card`'s own docstring says to
prefer *over* — IS used elsewhere (`burgs.py`, and per grep also `verify_math.py`,
`manifest_builder.py`, `catalog.py`, `generate.py`). So the "prefer `seed_from_card()`" note is
aspirational, not descriptive of current wiring. (Reproduces sweep30/AUDIT_batch05.md §4.4,
still unfixed.)

### 9. burgs.py:76, 121-125 — `GENERATORS` dict is dead code, and the field it should populate carries the wrong value  [severity: MINOR]
```python
GENERATORS = {"city": "Watabou city generator", "village": "Watabou village generator"}
...
def classify(pop):
    for name, lo, hi, gen in CLASSES:
        if lo <= pop < hi:
            return name, gen                 # gen is CLASSES' own literal "city"/"village"
    return CLASSES[-1][0], CLASSES[-1][3]
```
`GENERATORS` is never referenced anywhere in the file (confirmed by grep across all of `src/`).
`classify()` returns the raw `"city"`/`"village"` string straight out of `CLASSES`'s 4th column,
and `burgs_for()` stores that directly as `"generator"` in every burg record. The comment on
`GENERATORS` ("Which of Watabou's two generators a settlement belongs in. Recorded for
reference only") describes a lookup that never happens — every burg's `"generator"` field ends
up holding `"city"`/`"village"` (duplicating information already in `"class"`'s coarse bucket)
rather than the descriptive `"Watabou city generator"` / `"Watabou village generator"` string
the dict and the surrounding prose promise.

### 10. burgs.py:225-230 — the closing message claims a "sample of 50 worlds" that the code does not write  [severity: MINOR]
```python
if args.write:
    p = os.path.join(HERE, "data", "BURGS_SAMPLE.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(per_world, f, indent=2, ensure_ascii=False)   # every world; Hard Rule 0
    print(f"\nwrote {p} (sample of 50 worlds; the rest regenerate on demand)")
```
`per_world` is built from `worlds = WS.build_all()` — every world, correctly per Hard Rule 0
(the code's own comment says so). The print message directly below it still describes the old,
truncated behaviour ("sample of 50 worlds; the rest regenerate on demand"). The file name
(`BURGS_SAMPLE.json`) carries the same stale implication. Not a data bug — the write is
complete — but the console message and filename actively misinform whoever reads the run's
output about what was persisted.

### 11. snapshot.py:94-120 — `verify()` never compares directory contents, only that the destination path exists  [severity: MAJOR]
```python
for rel in m.get("took", []):
    a = os.path.join(ROOT, sid, rel.replace("/", os.sep))
    b = os.path.join(tmp, rel.replace("/", os.sep))
    if not os.path.exists(b):
        return False, "restore omitted %s" % rel
    if os.path.isfile(a) and not filecmp.cmp(a, b, shallow=False):
        return False, "restored bytes differ for %s" % rel
```
When `rel` names a directory (anything snapshotted via `shutil.copytree` in `before()`/
`restore()`), `os.path.isfile(a)` is `False`, so the byte-comparison branch is skipped entirely
— the only check that runs is `os.path.exists(b)`, which is true for any directory regardless
of its contents. A restore that dropped, truncated, or corrupted files nested inside a
snapshotted directory would still report `"N path(s) restored and byte-identical"`. This
directly contradicts the module's own stated purpose ("`verify(sid)` restores into a TEMPORARY
directory and compares bytes... An untested backup is a belief, not a backup") for exactly the
case — a directory — that most real callers would snapshot. Every net in `drill.py`'s
`drill_snapshot()` only ever exercises a single file (`config.yaml`, see finding #3), so this
gap has no test coverage anywhere in the battery either.

### 12. compress_store.py:43-44 — `store()` writes the final content-addressed file directly, not through `silence.replace_retry`  [severity: MAJOR]
```python
with open(path, "wb") as f:
    f.write(blob)
```
Every other shared-state writer read in this batch (`gpu_lane.py`'s `_write_claim`/`_touch`,
`weave_index.py`'s `silence.write_json` calls, `address_space.py`'s `silence.write_json`) goes
through a write-to-temp-then-atomic-replace helper specifically because a bare `open(path, "w"/
"wb")` leaves a torn or truncated file visible at its final path if the process dies mid-write
or another reader opens it concurrently — the exact hazard `gpu_lane.py`'s and `drill.py`'s own
comments describe at length (m55, run #19, run #31). `compress_store.store()` is the one writer
in this batch that still does the bare version: a kill or crash between `open()` and `f.write()`
completing leaves a half-written blob sitting at its permanent content-addressed path
(`{hash}.zst`/`{hash}.gz`), and because the store is content-addressed, nothing else will ever
retry or overwrite that path with the same content unless `store()` happens to be called again
for the identical text. A later `load()` of that hash will raise loudly on decompression rather
than returning silently-wrong data, which limits the blast radius, but the write itself is not
atomic where every comparable writer in this codebase has deliberately been made so.

## QUESTIONS
- Findings #4, #7, #8: is the H/X-charting change in `shelfmark()` (and the still-unwired
  `citation_card`/`seed_from_card`) a deliberate, reviewed step toward retiring the `Ω › ? › ?`
  placeholder project-wide, just with the docstrings and downstream wiring not yet caught up? Or
  is printing real H/X numbers itself premature ahead of Hard Rule 4's "leave it as `?` until
  that research exists"? This determines whether #4 is "update a stale comment" or "the code
  moved ahead of the ruling that was supposed to gate it."
- Finding #11: are there currently any real callers that snapshot a *directory* (as opposed to
  individual files) before a destructive step? If not yet, this is a landmine for the first
  caller that does, not an active one today — worth knowing before prioritising a fix.
- Finding #12: is `compress_store.py`'s non-atomic write a deliberate simplification (content
  is immutable and keyed by its own hash, so a torn write just fails loud on read rather than
  serving wrong data) or an oversight relative to the rest of the codebase's atomic-write
  discipline? The consequence differs a lot depending on whether anything reads a
  freshly-written hash concurrently with the writer.

## CLEAN
- `gpu_lane.py` — read in full. The Windows `_alive()` PID-liveness check, the heartbeat/lease
  machinery, `_take_slot`'s `O_CREAT|O_EXCL` exclusion, and the foreground/background yield
  logic in `lane()` all held up under inspection; every failure path does fail open as claimed,
  and the fixes documented in its own comments (m54, m55, run #19) look complete and consistent
  with the code as it stands today.
- `weave_index.py` — read in full. `designations()`/`load_records()` cache-invalidation
  (keyed on directory signature) is sound, `norm()`'s title-stripping and continuity-suffix
  logic is correct including the ternary precedence at line 162, and the cross-source candidate
  filter genuinely requires distinct sources. No findings.

Coverage recorded: batch=5, modules = drill.py, gpu_lane.py, address_space.py, weave_index.py,
burgs.py, snapshot.py, compress_store.py.
