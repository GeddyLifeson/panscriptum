# Sweep 24 — Batch 16 Audit

Files in batch, all read in full, line by line:

- `src/build_terminal.py` (580 lines) — complete
- `src/derivation.py` (559 lines) — complete
- `src/generate.py` (422 lines) — complete
- `src/pantheon.py` (309 lines) — complete
- `src/genre.py` (248 lines) — complete
- `src/chord_field.py` (204 lines) — complete
- `src/module_index.py` (84 lines) — complete

Also read for cross-reference (not part of the batch, not separately audited): `src/silence.py`
(to establish what "atomic" means here), `src/catalog.py:79-98` (to confirm the reader of
`generate.py`'s raw output), and `src/pipeline.py` (grep only, to confirm `write_record`
locations).

---

## 1. `build_terminal.py:468` (+ call sites 487, 503, 524) — `shelfmark()` bypasses the file's own escaping contract

```js
function shelfmark(k){
  let s="&#937;"; if(k==="") return s;
  const parts=k.split(".");
  for(let i=0;i<parts.length;i++){
    const key=parts.slice(0,i+1).join("."), nd=DATA.nodes[key];
    s+=" › "+((nd&&nd.name)||LABEL[TIERS[i]]+parts[i]);   // <-- nd.name, unescaped
  }
  return s;
}
```
splices directly into `innerHTML` at three sites with no `esc()`:
- `panel()`, line 487: `` <div class="mark">${shelfmark(k)}</div> ``
- `selectSource()`, line 503: `` <div class="mark">${shelfmark(rootKey)}</div> ``
- `selectWorld()`, line 524: `` <div class="mark">${shelfmark(rootKey)} › P<br>seed ${w.s}</div> ``

The file's own top-of-script comment (lines 80-84) states the invariant this violates:

> "Every catalogue-derived string goes through this before it reaches innerHTML. The names come
> from the roll and from wikis, so 'Dungeons & Dragons' is not a hypothetical... (BUGS m10,
> 2026-08-24.)"

Every OTHER place a catalogue name reaches `innerHTML` in this file goes through `esc()` —
verified by reading every `innerHTML`-bound template literal in the script (node titles/labels
in `draw()`, the roster list in `panel()`, `selectWorld()`'s `cat`/`endo`). `shelfmark()` is the
one path that was missed. A source or world name containing `&`, `<`, or `>` (the file's own
docstring cites `&` as a real, attested case) breaks the breadcrumb markup and everything
rendered after it in the side panel, the exact failure class m10 already fixed elsewhere in this
same file.

**Severity: MAJOR.** **VERIFIED** by reading `shelfmark()` and all three call sites, and
confirming no other escaping happens on that path.

Secondary, much smaller finding in the same function: `TIERS` (line 88) has 5 entries
(`hyperverse`..`universe`); `shelfmark()` indexes `TIERS[i]` for `i` up to `parts.length-1`,
which reaches 5 for a 6-segment (world-level) address. `TIERS[5]` is `undefined`, so the
unresolved-node fallback text becomes literally `"undefined" + parts[i]` for that one case.
Cosmetic, edge-case only (triggers when a world-depth key doesn't resolve to a `DATA.nodes`
entry). **Severity: MINOR/COSMETIC. VERIFIED** by reading the array and the indexing.

## 2. `build_terminal.py:571-573` — non-atomic write of the terminal HTML (known suspect, confirmed)

```python
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
```
Plain truncate-then-fill on `output/registry_terminal.html`, no `.tmp` + `os.replace`, no use of
`silence.write_json`/`silence.replace_retry`. A crash mid-write (or two overlapping invocations)
leaves a truncated or interleaved HTML file with no recovery. This is a direct instance of the
pattern Hard Rule 4 forbids ("direct `open(path,\"w\")` + ... on a shared file"). Mitigating
factor, checked directly: grep across `src/` shows nothing else programmatically reads
`output/registry_terminal.html` (only `pipeline.py`'s own doc-table mentions it as a browser
artifact) — so the live-collision risk is lower than a state file with an automated reader, but
the durability hazard (crash mid-write corrupts the only copy) stands regardless.

**Severity: MAJOR** (explicit two-writer-contract violation on a shared output file; lower
likelihood of concurrent-reader corruption, but no atomicity at all against a mid-write crash).
**VERIFIED.**

## 3. `module_index.py:75-76` — non-atomic write of `handoff/MODULE_INDEX.md` (known suspect, confirmed)

```python
with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
```
Same pattern as #2: no tmp file, no `os.replace`, no `silence` helper, despite `silence` already
being imported in this module (used correctly for `note()` at line 47). Confirmed via grep that
nothing in `src/` reads `handoff/MODULE_INDEX.md` programmatically — it's human-facing
documentation — so again the practical collision risk is low, but it is a literal Hard Rule 4
violation and the fix would be one line (`silence.write_json` doesn't apply since this isn't
JSON, but the same tmp+`replace_retry` pattern silence.py already implements for
`write_json`/`append_line` is directly reusable here and isn't used).

**Severity: MAJOR** (contract violation; low concurrency risk in practice). **VERIFIED.**

## 4. `derivation.py:476-477` — `SCAN_MODULES` silently omits `pantheon.py` and `zfighters.py`

```python
SCAN_MODULES = ["assay", "feats", "cosmography", "propagation", "descending_ladder",
                "scale_theories", "chord_field", "resonance", "tempus", "ledger", "rigor",
                "custodes", "weave", "onomast", "worldseed", "address_space", "genre",
                "profile", "tiers", "grounding", "sevenfold", "burgs"]
```
This list is the sole input to `scan_constants()`'s "where constants live" reviewer's map — the
file's own stated purpose is "so a reviewer can see exactly where numbers live and catch a new
undeclared one the day it is written rather than three volumes later." `custodes.py` is on the
list, and its own ledger entry (`custos_tilts`) explicitly calls its `CUSTODES` dict "THE LARGEST
BLOCK OF FREE PARAMETERS IN THE LIBRARY."

`pantheon.py` (in this same batch) and `zfighters.py` (confirmed to exist, same directory)
contain the structurally identical pattern — module-level uppercase dicts (`GODS` in
`pantheon.py`, `ROSTER` in `zfighters.py`) of dozens of hand-authored float axis scores (e.g.
`pantheon.py`'s `Zeno`/`Vados`/`Whis`/`Beerus`/`Champa`/`Grand Minister` axis tuples,
1.5–9.5 each) — but neither module is in `SCAN_MODULES`. Verified by enumerating every `.py` in
`src/` (95 total) against the list (22 entries): 73 modules are excluded, most legitimately
(infrastructure/supervision scripts with no ledger-relevant constants), but `pantheon.py` and
`zfighters.py` specifically hold exactly the kind of owner-declared numeric block the ledger
exists to surface, and their sibling `custodes.py` (same content shape) is included. This makes
the "where constants live" report silently incomplete for two modules whose numbers are of
direct relevance to the ledger's own stated purpose — a check that can't see the very thing it
was built to catch.

**Severity: MAJOR** (the scan's completeness claim is false for exactly the class of file it's
meant to flag; nothing errors, it just quietly doesn't look). **VERIFIED** by direct enumeration
(scripted diff of `SCAN_MODULES` against `glob(src/*.py)`, plus reading both omitted files' first
module-level assignments).

## 5. `generate.py:382-384` — non-atomic write of `output/raw/*.md`, races `catalog.py`'s reader on stale-job regeneration

```python
raw_path = os.path.join(raw_dir, safe_filename(job["address"], "md"))
with open(raw_path, "w", encoding="utf-8") as f:
    f.write(f"<!-- {job['address']} -->\n\n{text}")
```
Traced the consumer: `catalog.py:87-98` (`cmd_read`) does
```python
v = catalog.get(address)
...
raw_path = os.path.join(HERE, v["raw_path"])
if os.path.exists(raw_path):
    with open(raw_path, encoding="utf-8") as f:
        print(f.read())
```
`safe_filename()` derives the on-disk name purely from `job["address"]`, so a **stale**
regeneration (source data changed since the last run — this is a documented, expected code path,
not a corner case: `generate.py`'s own recipe-hash logic at lines 332-339 explicitly detects and
regenerates stale jobs) reuses the SAME filename as the previous successful generation. Sequence
on a stale job:

1. `generate_job()` returns new text.
2. `raw_path` is truncated and rewritten (non-atomically) — during this window the file on disk
   is empty or partial.
3. Only afterward is `catalog[job["address"]]` updated in memory, and only flushed to
   `catalog.json` on disk every 5 completions or at the very end (line 409-410).

Between steps 2 and 4, `catalog.json` on disk still carries the **old** (still-valid-looking)
entry for that address, pointing at the exact path currently being truncated in step 2. Since
`generate.py` is confirmed to be a currently-running, long-lived process, and the project's own
documented workflow (`CLAUDE.md`: "Querying what's generated" →
`python3 src/catalog.py read "II.A.3/Persons#1-30"`) tells the owner to run `catalog.py` while
generation is in flight, this is a live, reachable two-writer/reader race, not a theoretical one:
a concurrent `catalog.py read` on a stale address can return truncated or empty prose during that
window, indistinguishable from a legitimately short entry.

**Severity: MAJOR.** **VERIFIED by code tracing** (recipe-hash staleness path, filename
derivation, write ordering, and the confirmed downstream reader in `catalog.py`); not reproduced
against the live running process, since that would mean writing to `panscriptum-library-kit`
concurrently with the in-flight run rather than only auditing it.

Note for contrast: `save_json()` in this same file (line 53-58) already does this correctly via
`silence.write_json` for `catalog.json`/`failures.json` — the fix pattern is sitting three lines
above the bug.

## 6. `generate.py:271-300` — chunked entry-writing loop doesn't fail fast

```python
for gi, g in enumerate(groups):
    ...
    if lacking:
        raise RuntimeError("feats block omitted: " ...)   # (feats path only, not this loop)
    ...
    missing.extend(e.get("name", "?") for e in lacking)
if missing:
    raise RuntimeError(f"entries not written after retry: ...")
```
For the entries path (the `else` branch at line 271 handling ordinary chapters), a block that is
still missing entries after its own retry does **not** stop the job — `missing` is extended and
the loop proceeds to call Ollama for every remaining block, then raises only after all blocks
have been attempted. Since the job is already guaranteed to fail once any block comes up short
(the `if missing: raise` after the loop is unconditional), every subsequent block's two Ollama
calls (primary + retry) are pure waste — no correctness impact (the exception is still raised and
the failure is still filed with a full, accurate list of missing names), but it costs a full
model call per remaining block for a job already known to fail.

**Severity: MINOR** (inefficiency, not a correctness bug — the job still fails correctly and is
still retried whole on the next run). **VERIFIED.**

## 7. `pantheon.py:263-271` — Z_FIGHTERS merge failure is logged but not surfaced to the CLI user

```python
if not a.gods_only:
    for path in ("Z_FIGHTERS.json",):
        try:
            with open(os.path.join(HERE, "data", path), encoding="utf-8") as f:
                for k, v in json.load(f).items():
                    combined.setdefault(k, v)
        except Exception:
            silence.note("pantheon.py:merge")
```
This satisfies the project's own SILENCE discipline — the failure is recorded via
`silence.note()` (logged to `health`, not a bare `pass`), so it does not count as one of the
project's signature swallowed failures under `silence.py`'s own audit definition. But the
printed report (`main()`'s ranking table) gives the person running `pantheon.py --full` no
on-screen indication that `Z_FIGHTERS.json` failed to load — the table would just quietly show
6 gods instead of gods + Z Fighters, with no visible reason, and the only trace is a `health`
record the user isn't looking at. `data/Z_FIGHTERS.json` is itself written by `zfighters.py`
(not in this batch, not audited here) — if that write is also non-atomic, this read could
legitimately race it.

**Severity: MINOR/COSMETIC** (failure is observed per project convention, but the user-facing
output doesn't say why the table is short). **VERIFIED.**

---

## Files confirmed clean

- **`chord_field.py`** — pure physics/reference module, no I/O, no shared state, no writes. All
  formulas checked against their named sources (Marburger self-focusing critical power, Landauer
  bound, photon momentum `p=E/c`) and match. Constants (`C_LIGHT`, `G_NEWTON`, `HBAR`,
  `K_BOLTZMANN`) cross-checked against `derivation.py`'s ledger `MEASURED` values for `c`, `G`,
  `hbar`, `k_B` — consistent. No findings.

- **`genre.py`** — the `cap` parameter is correctly hard-refused (`raise SystemExit` for any
  non-`None` value, Hard Rule 0 compliant, matches the documented history in its own docstring).
  Single write site (line 241) uses `silence.write_json` correctly — confirmed this is the ONLY
  write in the file, no half-converted leftover `open()+json.dump` anywhere else. No unused
  imports. No findings beyond what's noted above.

- **`pantheon.py`** — single write site (line 261) uses `silence.write_json` correctly, confirmed
  the only write in the file. No unused imports (`json` is used for the `Z_FIGHTERS.json` read).
  Conversion to `silence.write_json` for both `genre.py` and `pantheon.py` is complete and
  correct at every write site in both files — no site was missed, no half-converted path exists.

- **`module_index.py`** — no duplicate module listings across `GROUPS` (checked by script), no
  hidden caps, correctly falls back to "Everything else" for ungrouped modules. Only finding is
  the non-atomic write (#3 above).

- **`derivation.py`** graph-integrity logic (`check_graph`, cycle detection via `visit()`,
  `depth()`) — correct standard DFS cycle detection, no infinite recursion risk even with a
  cycle present (state machine terminates), no off-by-one. The `[:6]` in the "deepest derivation
  chains" printout and `pending[:3]` in `--dry-run` are transparent, labeled display truncations
  (both explicitly print how many were shown of how many total) — not Hard Rule 0 violations.

- **`generate.py`** `save_json`/catalog/failures handling — already correctly migrated to
  `silence.write_json` (per its own 2026-08-25 comment); `context_budget.assert_fits` correctly
  refuses an over-long prompt before sending rather than letting Ollama truncate it silently;
  failure vs. success is otherwise cleanly distinguishable (catalog only updated on success,
  failures.json records every exception with type/timestamp); no evidence the process itself can
  wedge (network calls are timeout-bounded via `request_timeout`, default 600s; no locks or
  polling loops in this file). One resource worth flagging for separate review, **out of this
  batch's scope**: `gpu_lane.lane("generate", priority=True)` (imported at line 155, defined in
  `gpu_lane.py`, not part of this batch) is held across every `requests.post` call — if that
  context manager can itself block indefinitely under contention, or fails to release on an
  exception, it would look exactly like "generate.py wedged" from outside. Not verified either
  way; flagging as a boundary the currently-running process depends on that this batch didn't
  cover.
