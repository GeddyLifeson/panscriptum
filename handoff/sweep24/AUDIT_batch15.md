# Batch 15 audit — sweep run #24

Files in batch, all read in full, every line:
- `src/wiki_source.py` (616 lines) — read completely.
- `src/local_agent.py` (541 lines) — read completely, audited hardest per instructions, with live
  reproduction of the gate-bypass finding below on this machine (Windows/NTFS).
- `src/rosetta.py` (408 lines) — read completely.
- `src/address.py` (290 lines) — read completely.
- `src/tempus.py` (254 lines) — read completely.
- `src/cleanup.py` (208 lines) — read completely.
- `src/resync_roll.py` (81 lines) — read completely.

Cross-checked against `src/pipeline.py` and `src/verify_math.py` (grep only, not full-line audit,
to verify specific claims below) and `src/silence.py` (grep only, to characterize
`write_json`/`replace_retry` semantics referenced by this batch).

---

## 1. `local_agent.py:365-438,298-362` — Alternate Data Stream suffix defeats the denylist AND
   the parse/lint/import gates for `propose_patch`. **MAJOR. VERIFIED (live-reproduced).**

```python
modname = os.path.basename(full)[:-3] if full.endswith(".py") else None
...
rel = os.path.relpath(full, HERE).replace(os.sep, "/")
...
denied = (modname if _mod_l in _deny
          else (rel if rel.lower() in _deny_paths else None))
```
and in `_gates()`:
```python
if full.endswith(".py"):
    try:
        ast.parse(open(full, encoding="utf-8").read())
    ...
if full.endswith(".py") and modname:
    r = subprocess.run([PY, "-c", "import ... import %s" % modname], ...)
```

**What goes wrong.** Both the denylist test and the `.py`-specific gates (`ast.parse`,
pyflakes, `import <modname>`) key off `full.endswith(".py")` and off `modname`/`rel` computed
from `full`. NTFS lets a path be suffixed with `::$DATA` — the name of a file's own *unnamed*
default data stream — and Windows treats `<file>::$DATA` as a fully valid alias for `<file>`
itself for open/read/write/`os.path.isfile`, while the *string* no longer ends in `.py`.

If the local model calls `propose_patch(path="src/foreman.py::$DATA", find=..., replace=...)`:

1. `_safe()` accepts it — the ADS suffix doesn't change directory boundaries, so `full` still
   resolves inside `HERE` and passes.
2. `full.endswith(".py")` is **False**, so `modname = None`.
3. `rel = "src/foreman.py::$DATA"`, which is **not** in `DENYLIST_PATHS` (`{"config.yaml"}`).
4. `denied` evaluates to `None` — **the denylist is bypassed entirely** for `foreman`, `silence`,
   `standards`, `verify_math`, `health`, `allsweep`, `estate`, and `local_agent.py` itself (the
   exact set the comment at line 376-382 says was already fixed for the case-sensitivity bug).
5. `open(full, ...)` reads and `open(full, "w", ...)` writes the **real** `foreman.py` content —
   NTFS routes the named-stream-with-empty-name syntax straight to the file's actual bytes.
6. In `_gates(full, modname)`: `full.endswith(".py")` is again False, so the `ast.parse` /
   pyflakes / `import <modname>` checks are **all skipped**. Only the unconditional whole-suite
   `verify_math.py` run remains.

**Live reproduction** (scratch file, not a project file):
```
target = scratch/ads_test.py containing "ORIGINAL_CONTENT_MARKER"
open(target + "::$DATA", "w").write("MUTATED_VIA_ADS")
-> real file's content is now "MUTATED_VIA_ADS"
os.path.isfile(target + "::$DATA") -> True
(target + "::$DATA").endswith(".py") -> False
```
This confirms the write-through and the extension-check defeat exactly as used by
`t_propose_patch`/`_gates`.

**Concrete failure scenario.** The model proposes a patch to `src/foreman.py::$DATA` (a path
string it could arrive at accidentally via its own path-construction, or that a sufficiently
capable/adversarial local model could construct deliberately once it has seen this file's own
denylist comments via `read_file`, which explicitly names `foreman`/`silence`/`standards` etc.
as protected). The patch bypasses the "checking machinery may not edit itself" rule the
denylist exists to enforce, and lands with only the whole-suite `verify_math.py` gate as a
backstop.

**That backstop is not uniform across the denylist.** Checked which denylisted modules
`verify_math.py` actually imports (so a syntax break would be caught indirectly even with the
per-file gates skipped):
- `foreman`, `silence`, `standards` — **are** imported by `verify_math.py`, so a *syntax*-
  breaking edit via this bypass would likely still surface as `verify_math` failing to reach
  "0 FAILED" and get reverted.
- `health`, `allsweep`, `estate`, `local_agent` — **verify_math.py never imports these at all**
  (confirmed by grep — zero hits for `import health|import allsweep|import estate|import
  local_agent`). For these four files, the ADS bypass leaves **zero gates active**: no parse
  check, no lint, no import check, and the whole-suite gate is structurally blind to any damage
  done to them. A patch to `src/local_agent.py::$DATA` (this file editing itself) or
  `src/health.py::$DATA` would be applied with no verification whatsoever and reported
  `"applied": True`.

Also generalizes to the non-Python denylist: `config.yaml::$DATA` has `rel =
"config.yaml::$DATA"`, which is not in `DENYLIST_PATHS = {"config.yaml"}`, so the same bypass
applies to the config file the docstring specifically calls out as protected.

**Fix direction (not applied — audit only):** compute `modname`/`rel`/the denylist test from a
stream-stripped form of the path (split on the first unescaped `:` after the drive letter, or
reject any path containing `:` beyond the drive-letter position), not from the raw string
handed to `open()`.

---

## 2. `local_agent.py:407-438` — "backup" is held only in process memory, never written to disk,
   despite the module docstring's promise. **MINOR (doc/code contradiction). VERIFIED.**

```python
backup = original
try:
    with open(full, "w", encoding="utf-8") as f:
        f.write(original.replace(find, replace, 1))
    fail = _gates(full, modname)
    if fail:
        with open(full, "w", encoding="utf-8") as f:
            f.write(backup)
```

The module docstring (lines 16-21) states: *"A backup is written before and restored on ANY
failure, including a crash inside the checking."* No backup file is ever written to disk
anywhere in this function — `backup` is a Python variable holding the pre-patch text in memory.
If the process is killed (OS kill, power loss, a hung subprocess timeout that the user
Ctrl-C's) between the first `f.write()` and the revert, the mutated file is left on disk with no
recorded backup anywhere — the in-memory copy is gone with the process. The revert-on-exception
path (lines 417-438) is real and does correctly restore on any *caught* exception, including
gate failure and I/O errors during the write itself — that part of the docstring's claim holds.
Only the "written" word is inaccurate: it is retained, not persisted, so the guarantee has a gap
exactly at the failure mode (hard kill) the docstring's own phrase ("including a crash inside
the checking") seems to be trying to cover.

---

## 3. `wiki_source.py:352-389` — `all_categories(hard_stop=6000)` truncates the returned category
   list alphabetically for large wikis; docstring claims it only bounds the API walk.
   **MAJOR (Hard Rule 0). VERIFIED (live MediaWiki API check).**

```python
def all_categories(subdomain, min_pages=40, hard_stop=6000):
    """...
    `hard_stop` bounds the API walk, not the answer: it exists so a wiki with a hundred
    thousand year-buckets cannot spin here forever.
    """
    ...
    out, cont = [], None
    while len(out) < hard_stop:
        p = {"action": "query", "list": "allcategories", "aclimit": 500,
             "acmin": min_pages, "acprop": "size"}
        if cont:
            p["accontinue"] = cont
        ...
        cont = d.get("continue", {}).get("accontinue")
        if not cont:
            break
    ...
    return out
```

Live-checked the MediaWiki `list=allcategories` API directly against `dc.fandom.com` (no
`acdir` parameter is passed anywhere in this code, so the API default applies):

```
curl "https://dc.fandom.com/api.php?action=query&list=allcategories&aclimit=10&acmin=40&acprop=size&format=json"
-> "100 Bullets/Images", "100 Bullets Vol 1", ... "16th Century/Appearances" ...
```

confirming the walk proceeds strictly alphabetically from `accontinue` cursors. The loop's own
exit condition is `while len(out) < hard_stop` — once 6000 categories (meeting `min_pages`) have
been collected, the walk stops **and `out` is returned and cached as the wiki's complete answer**
for that `(subdomain, min_pages)` key (`_ALLCATS[key] = out`, consulted by every later caller of
`discover_categories`/`find_categories`). For any wiki whose category count at the given
`min_pages` threshold exceeds 6000, this silently returns only the alphabetically-first ~6000 and
drops every category sorting after the cutoff — which is exactly the truncation-wearing-a-
completed-shape Hard Rule 0 forbids, not merely a defensive walk-bound as the docstring claims.
This is the documented DC/Superman incident referenced in the audit brief; the code as it stands
today still has this shape.

---

## 4. `rosetta.py:194` — `srlimit="5"` caps candidate scale-page discovery per search term.
   **MINOR-MAJOR (Hard Rule 0, narrower blast radius than wiki_source's). VERIFIED (code
   reading — this is the exact known suspect line).**

```python
d = F.api(host, {"action": "query", "list": "search", "srlimit": "5", "srsearch": q})
```

`scales_for()` runs this once per entry in `SCALE_QUERIES` (25 query strings) to find candidate
pages that might hold a native power scale, then filters by title regex and page size. Only the
top 5 search hits per query are ever considered; any genuine scale page ranking 6th or lower for
every one of the 25 queries it might match is never discovered, silently narrowing which of a
wiki's native scales get mined and cross-checked against the Assay. This is a real listing cap,
though its damage is bounded by the fact that 25 differently-worded queries are tried per wiki
(a page has many chances to surface), unlike the `wiki_source.py` case above where a single
alphabetical walk is the only path to an entity.

---

## 5. `rosetta.py:364-366` and `:377-378` — direct `open(path, "w")` + `json.dump` for
   `data/ROSETTA.json`, not `silence.write_json`/`replace_retry`. **MAJOR (two-writer contract).
   VERIFIED.**

```python
for path in (OUT, OUT.replace(".json", ".raw.json")):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
```
and (in `--refine`):
```python
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
```

`data/ROSETTA.json` is shared state, read back by this same module's `--check` and `--refine`
modes and written by both `--mine` and `--refine`. Per `silence.py`'s own `write_json`
docstring (confirmed by reading it directly), a bare `open(path,"w")` is "not a write but a
TRUNCATE-THEN-FILL": a reader arriving in the gap sees a truncated/empty file, and a crash mid-
write leaves it that way permanently — `silence.write_json` exists specifically to fix this
class of bug project-wide and was already retrofitted into `resync_roll.py` for the sibling file
`SWEEP_ROLL.json` (see finding 7). `rosetta.py` was not updated to match. Own-authored comment
at line 361-363 ("`--refine` is destructive and was run against a stale raw copy once, which
silently discarded a good 3,514-row mine") shows this exact file has already lost real data to a
write-ordering hazard once; the fix applied there was procedural (write the `.raw.json` sibling
first) rather than making the write itself atomic, so the underlying hazard (truncated file on
crash, or two `rosetta.py --mine`/`--refine` invocations racing) remains open.

---

## 6. `rosetta.py:394` — `P.__dict__.get("_x", 0)` added to every Assay decimal used for
   `--check`. **MINOR (latent correctness hazard, currently a no-op). VERIFIED — `_x` does not
   exist in `pipeline.py` today (grep: zero hits), so this evaluates to `+0` right now.**

```python
assays = {k: v["result"]["decimal"] + P.__dict__.get("_x", 0)
          for k, v in json.load(open(path, encoding="utf-8")).items()
          if v.get("result") and v["result"].get("decimal") is not None}
```

Reaching into another module's `__dict__` for an undocumented, unused attribute name to add to
every calibration value is unexplained by any comment and has no purpose visible in either
`rosetta.py` or `pipeline.py` today. It is inert now only because `pipeline.py` happens not to
define `_x`. Python leaks loop variables to module scope when a `for` loop runs at module level
(e.g. a stray top-level `for _x in ...:` added to `pipeline.py` in the future), which would
silently shift every single Assay decimal this check compares against native scales by whatever
that variable's last value was, with no error raised anywhere — the exact "swallowed failure
disguised as a legitimate number" shape this project's audits watch for. Recommend removing this
term or replacing it with a named, documented constant if a calibration offset is genuinely
intended.

---

## 7. `resync_roll.py` — write is now atomic (fixed), but the read-modify-write cycle around
   `data/SWEEP_ROLL.json` is still a lost-update race against concurrent writers; docstring's
   "safe to run at any time" overstates what was fixed. **MINOR. VERIFIED (code + cross-check of
   `silence.write_json`'s actual guarantees).**

```python
with open(ROLL, encoding="utf-8") as f:
    roll = json.load(f)
...
for r in roll:
    ...
    r["entry_count"] = n
    ...
if changed and not dry:
    silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)
```

The comment at line 66-67 ("ATOMIC: ... Fixed 2026-08-25") is accurate as far as it goes —
`silence.write_json` does write via a PID/thread-unique temp file plus `os.replace` (confirmed
by reading `silence.py`), so this script's own write can no longer land as a truncated or
corrupted file, and it no longer collides on a shared fixed temp filename with a sibling writer.
That is a real fix and closes the *corruption* half of the hazard this module's own docstring
describes (multiple cataloguers clobbering the roll with stale in-memory copies).

It does not close the other half. `roll` is read once at the top of `main()`, then the entire
list is rewritten at the end reflecting only this script's own diffs; anything a *concurrent*
writer (one of the four cataloguers, or another invocation of this same script) commits to
`SWEEP_ROLL.json` in between this script's read and its write is silently discarded when this
script's write lands — a classic TOCTOU lost-update, not fixed by making the individual write
atomic. The docstring's claim "It is safe to run at any time and changes nothing else about the
roll" is true of *what fields it touches* but not true as a race-safety claim: running this
script during an active cataloguing session (a scenario the docstring's own opening paragraph
describes as normal and expected) can still lose that session's concurrent counter update if the
timing lands inside this script's read-to-write window.

---

## 8. `cleanup.py:174-177` — `thin_description` marking is set in memory but not persisted when
   it is the only change made to a record. **MAJOR (silent write loss). VERIFIED.**

```python
cd = clean_description(d)
if cd != d:
    desc_fixed.append((src, nm, d[:46], cd[:46]))
    if args.apply:
        e["description"] = cd
        changed = True
if len(cd) < _THIN:
    thin.append((src, nm, cd))
    if args.apply:
        e["thin_description"] = True
...
if changed:
    PL.write_record(path, rec)
```

`changed` is set to `True` by the nav-exclusion branch, the empty-mechanic branch, and the
markup-cleanup branch — but **not** by the thin-description branch. If an entry's description is
short enough to trip `_THIN` (15 chars) but requires no markup cleanup and the record has no
navigation/empty-mechanic entries elsewhere, `e["thin_description"] = True` is set on the
in-memory `rec` dict and then thrown away: `changed` is still `False`, so `PL.write_record(path,
rec)` is never called for that record. Run with `--apply`, `cleanup.py` will print `"4.
descriptions too thin to write from : N (marked, not deleted)"` claiming N entries were marked,
while for every record where that was the *only* qualifying change, nothing was actually written
to disk. The console report and the on-disk state disagree, and there is no error or log entry
indicating the loss — it satisfies this project's own definition of a swallowed failure (a real
effect silently not happening while being reported as having happened).

---

## 9. `cleanup.py:162` — empty-mechanic strikes are folded into the "wiki navigation" report
   bucket. **COSMETIC (reporting only; the actual exclusion logic is correct and distinct).**

```python
if not d.strip() and _EMPTY_MECHANIC.search(nm):
    nav.append((src, nm + "  [empty mechanic]"))
```

Both `_NAV` matches (true wiki navigation pages) and `_EMPTY_MECHANIC` matches (rules-construct
entries with no description) are appended to the same `nav` list, then reported under the single
heading `"1. wiki navigation removed from the catalogue"`. The `[empty mechanic]` suffix
disambiguates in the detail lines, but the summary count conflates two different defect classes
described separately in the module's own docstring. Behavior (exclusion) is correct; only the
console summary's count/label is imprecise.

---

## Clean / no findings

- `src/address.py` — read in full. Careful, well-commented fallback chain for
  `spine_code_for()` (exact match -> normalized equality -> word-boundary containment -> token
  overlap), each step's rationale backed by a specific past-bug comment and the stated 215-entry
  regression check. `promote()`'s promotion-only-never-demotion logic is sound and intentional.
  No caps, no swallowed failures, no shared-write hazard (this module does no I/O beyond a
  cached read of `CHARTER_SPINE_CODES.json`). No findings.
- `src/tempus.py` — read in full. Pure-function math module (Spearman-free here; that's
  `rosetta.py`), no file I/O, no concurrency, no caps. `band_resolution()`'s edge-index handling
  for the first/last rung checked and correct. No findings.
