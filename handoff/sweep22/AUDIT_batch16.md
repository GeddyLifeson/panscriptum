# Batch 16 audit — build_terminal.py, derivation.py, rosetta.py, pantheon.py, render.py, coverage.py, catalog.py

Full top-to-bottom read of all seven files. Every finding below is cited `file.py:LINE` with the
actual code quoted, and labeled VERIFIED (confirmed by reading the code, and by execution/grep
where noted) or UNVERIFIED (plausible from the code but depends on data/runtime state I did not
have access to).

---

## HIGH

### H1 — rosetta.py:104-105, never called — the Stand-stat parser is dead code; JoJo-style scales are silently never mined

```python
# rosetta.py:104-105
_STAND = re.compile(
    r"\b(power|speed|range|durability|precision|potential)\s*[:=|]\s*([A-E])\b", re.I)
```

`_STAND` is referenced exactly twice in the whole file: its own definition, and a comment at
line 92 ("Stand stats are read from their parameter block instead (see `_STAND`)"). It is never
called — not from `numeric_rows`, not from `ordinal_rows`, not from `scales_for`. Confirmed by
grep across the file: the only two hits for `_STAND` are the definition and the comment.

The module's own docstring (line 6-7) names "Stand statistics" as one of the flagship examples
of a native scale this file is built to mine, and `ORDINAL_LADDERS`'s own comment (lines 88-92)
explains at length *why* single-letter grades need this special-cased parser rather than the
generic ladder matcher — and then the parser that comment promises is simply never wired in.
The practical effect: any wiki whose native scale is a labelled A-E parameter block (JoJo's
Bizarre Adventure being the explicit motivating case) contributes **zero** rows to
`scales_for()`'s output, with no error, no log line, nothing — it just looks like that wiki
"doesn't publish a scale," identical in shape to a genuine absence. That is exactly the failure
mode the project's own `silence.py` charter describes as the most expensive kind (a defect that
"lands in exactly the shape the design trusts").

**VERIFIED** (absence of any call site confirmed by `grep -n "_STAND" rosetta.py`).

**Suggested repair**: call `_STAND` from `scales_for()` (or a new `stand_rows()`) as a third
parse path alongside `numeric_rows`/`ordinal_rows`, gated the same way ordinal ladders are
(only tried when the numeric pass comes back under 8 rows).

---

### H2 — rosetta.py:194 — MediaWiki search truncated to 5 results per query, silently dropping candidate scale pages

```python
# rosetta.py:194
d = F.api(host, {"action": "query", "list": "search", "srlimit": "5", "srsearch": q})
```

`scales_for()` runs 25 different search terms (`SCALE_QUERIES`) against every wiki host, and each
one is capped to the top 5 MediaWiki search results (`srlimit: "5"`). This is a page-list cap of
exactly the shape Hard Rule 0 forbids: it ranks (MediaWiki's own relevance ranking) and then
truncates, discarding every candidate scale page beyond the 5th most relevant hit for that term.
A wiki with, say, six or seven pages matching "rank system" or "grade sorcerer" would have the
long tail of those pages silently never fetched, never parsed, and never counted — with nothing
in the output distinguishing "we found 5 and that's genuinely all there are" from "we found 5
because that's the ceiling we asked for."

In mitigation: there are 25 overlapping query terms per host, so a real scale page is likely to
surface via *some* query even if not the "best" one — this softens but does not eliminate the
risk (a query with unusually many matches, e.g. a franchise with many rank/tier pages, is exactly
the case where the 6th+ result is most likely to matter).

**VERIFIED** (the literal `srlimit` value is hardcoded in the API call).

**Suggested repair**: either drop `srlimit` to the MediaWiki default/max and page through results
with `sroffset` until exhausted, or raise it substantially (MediaWiki allows up to 500 per call)
and document why 5 is believed sufficient if it's kept.

---

### H3 — coverage.py:182-183 — writes the library's headline coverage figures with a bare `open(path,"w")`, not `silence.replace_retry`

```python
# coverage.py:182-183
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=1, ensure_ascii=False)
```

`OUT` is `data/COVERAGE.json` — per the task brief, the file "every panel and standard reads."
This write is a plain, non-atomic `open(path, "w")` directly on the shared output file, not the
project's own documented pattern for shared/state files. Contrast with this very file's own
`_so_save()` two lines above (line 68-79), which writes to a `.tmp` file and calls
`silence.replace_retry(tmp, _SO_CACHE_P)` specifically *because* — per `silence.py:224-229`'s own
documentation — "this project's state files all have readers on their own clocks (the dashboard
polls records and ASSAYS, standards scans readfeats)," and a collision of exactly this kind
already took an assay worker down mid-batch on 2026-08-23 (WinError 5, file rename denied while
a reader had the target open).

`COVERAGE.json` is precisely the kind of file that gets polled by other panels while this script
runs — the task description says so explicitly. As written, any panel that has the file open for
read at the moment `measure()` finishes and `main()` starts writing risks either a Windows
`PermissionError` crash on this process, or (on platforms without that failure mode) a reader
observing a truncated/partial JSON document mid-write, since there is no atomic rename here.

**VERIFIED** (code as written; the WinError-5 precedent and the "readers on their own clocks"
rationale are silence.py's own documented history, not speculation).

**Suggested repair**: write to `OUT + ".tmp"` and call `silence.replace_retry(tmp, OUT)`, exactly
as `_so_save()` two lines above already does for the cache file.

---

## MEDIUM

### M1 — rosetta.py:364-366, 372-378 — `data/ROSETTA.json` (+ `.raw.json`) written non-atomically

```python
# rosetta.py:364-366 (inside --mine)
for path in (OUT, OUT.replace(".json", ".raw.json")):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
```
```python
# rosetta.py:377-378 (inside --refine)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
```

Same two-writer-contract gap as H3, on a different shared data file. `--mine` runs a long,
interruptible crawl across every wiki host (the file's own comment at line 361-363 already
acknowledges `--refine` running against "a stale raw copy" has burned this project once before —
"silently discarded a good 3,514-row mine and replaced it with the output of the parser that had
already been fixed"). A non-atomic write here means a Ctrl-C or crash mid-`json.dump` — likely
given how long `--mine` runs over many hosts — can leave `ROSETTA.json` truncated/corrupt rather
than either fully old or fully new.

**VERIFIED.**

**Suggested repair**: route both writes through `silence.replace_retry` via a `.tmp` file, as
`coverage.py`'s own cache-save function already models.

---

### M2 — pantheon.py:260-261 — `data/PANTHEON.json` written non-atomically

```python
# pantheon.py:260-261
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
```

Same class of finding as H3/M1: `data/PANTHEON.json` is a shared data output, written with a
plain `open(path, "w")` rather than through `silence.replace_retry`.

**VERIFIED.**

---

### M3 — pantheon.py:264-271 — bare `except Exception` conflates "no Z_FIGHTERS.json yet" with "Z_FIGHTERS.json is broken"

```python
# pantheon.py:264-271
if not a.gods_only:
    for path in ("Z_FIGHTERS.json",):
        try:
            with open(os.path.join(HERE, "data", path), encoding="utf-8") as f:
                for k, v in json.load(f).items():
                    combined.setdefault(k, v)
        except Exception:
            silence.note("pantheon.py:merge")
```

This is exactly the shape `silence.py`'s own charter singles out as the project's one recurring
defect: a broad `except Exception` around a block that can fail for very different reasons —
`FileNotFoundError` (benign: the file hasn't been generated yet), `json.JSONDecodeError` (the
file exists but is corrupt/truncated, e.g. from another instance of this exact bug), or a
`KeyError`/`AttributeError` from a schema mismatch inside the loop (a real defect in the merge
logic itself). All three are caught identically, logged with the same `silence.note` site string,
and the ranking silently proceeds as gods-only with no indication in the printed report that
anything was skipped, or why. `silence.note` does record *that* something failed, but the single
call site can't distinguish "expected" from "should be investigated," which is the specific
distinction `silence.py` was built to preserve.

**VERIFIED** (the `except Exception` is unqualified as written).

**Suggested repair**: catch `FileNotFoundError` separately (silently skip, expected) from
everything else (log loudly / re-raise), so a corrupt `Z_FIGHTERS.json` doesn't look identical to
a merely-absent one.

---

### M4 — render.py:166 — merging `sources` and `worlds` pools with dict-spread silently drops name collisions

```python
# render.py:166
pools = {**tree.get("sources", {}), **tree.get("worlds", {})}
```

`{**a, **b}` resolves key collisions by letting `b` win with no detection, logging, or warning.
If any name in `tree["sources"]` is identical to a name in `tree["worlds"]` (two different
populations from two different parts of the pipeline, with no guarantee of disjoint keyspaces),
the `sources` entry for that name vanishes from `pools` entirely and is replaced by the `worlds`
entry's coordinate data. Since `children_of()` uses `pools` to build the per-tier bucket counts
that `containment_svg()` renders as "N children" and as node weights, a collision would silently
undercount and/or misattribute an entry in the rendered diagram — with nothing in the output
indicating that a merge conflict occurred.

**VERIFIED** as written (the merge behavior is unambiguous Python). **UNVERIFIED** whether an
actual collision currently exists between the `sources` and `worlds` keyspaces in
`data/SEVENFOLD.json` — I did not have grounds to inspect that data file's actual key population
as part of a source-code read, so I can't say whether this is presently live or latent.

**Suggested repair**: build `pools` by iterating both dicts explicitly and either namespacing keys
(e.g. `("source", name)` / `("world", name)`) or asserting the keysets are disjoint and logging
via `silence.note` if not.

---

### M5 — rosetta.py:394 — dead reference to an attribute (`_x`) that is never defined anywhere in the codebase

```python
# rosetta.py:394-396
assays = {k: v["result"]["decimal"] + P.__dict__.get("_x", 0)
          for k, v in json.load(open(path, encoding="utf-8")).items()
          if v.get("result") and v["result"].get("decimal") is not None}
```

`P` is the `pipeline` module. `P.__dict__.get("_x", 0)` reaches into `pipeline`'s module
namespace for an attribute called `_x`. A project-wide grep (`grep -rn "_x" *.py` in `src/`)
turns up no definition of `_x` anywhere — not in `pipeline.py`, not anywhere else — so this
expression always evaluates to `0` today and the `+ P.__dict__.get("_x", 0)` term is a no-op.

This sits inside `check()`'s ground-truth construction — the exact function that scores whether
the Assay's rankings agree with each fiction's own published power scale. It reads like a
forgotten debug/calibration hook (perhaps once used to nudge decimals during testing) that never
got removed. It does no harm today because it is always zero, but it's dead code in the one
function this batch was asked to scrutinize hardest for arithmetic correctness, and any future
edit to `pipeline.py` that happens to define a module-level `_x` for an unrelated reason would
silently start perturbing every Rosetta accuracy check with no explanation.

**VERIFIED** (confirmed by `grep -n "_x" *.py` across `src/` — only match besides this line is an
unrelated `Delta_x` physics variable in `descending_ladder.py`).

**Suggested repair**: remove `+ P.__dict__.get("_x", 0)` entirely, or if it was meant to name a
real constant, wire it to one explicitly instead of a silent `__dict__.get` fallback.

---

## LOW

### L1 — coverage.py:103 — stale log-site label doesn't match its own line number

```python
# coverage.py:99-104
try:
    with open(fp, encoding="utf-8") as f:
        d = json.load(f)
except Exception:
    silence.note("coverage.py:60")
    continue
```

The literal string `"coverage.py:60"` is a leftover from an earlier version of the file where
this handler apparently sat at line 60; it's now at line 103. Harmless functionally (it's just a
label passed to `silence.note`), but it actively misleads anyone using `silence.py --failures` to
triage: they'll be pointed at the wrong code. Purely cosmetic but worth a one-line fix given how
much this project's own tooling leans on these site strings for debugging.

**VERIFIED.**

### L2 — coverage.py:141-158 — `report()` divides by `n` (total entries) with no zero-guard

```python
# coverage.py:142, 151
n = sum(r["entries"] for r in rows)
...
print(f"\n  CITED       {cited:>8,}  {cited/n:>6.1%}   carries a verbatim feat")
```

If `measure()` ever returns `rows` summing to zero total entries (e.g. `P.records()` yields
nothing), this is a bare `ZeroDivisionError` crash. `measure()` itself already guards the
per-row `coverage`/`settled` ratios with `max(n, 1)` (line 135-136), so the pattern is known to
the author — it just wasn't carried through to the aggregate totals in `report()`. Low severity:
it requires an essentially-empty catalogue to trigger, and failing loudly here (rather than
printing a nonsense percentage) is arguably the right behavior anyway — flagging for awareness,
not as something that necessarily needs fixing.

**VERIFIED** (edge case only, not currently triggered under normal data).

### L3 — Unclosed file handles (resource-leak style, not a practical leak)

Several `open(...)` calls across this batch are used without a context manager or explicit
`.close()`, relying on CPython's prompt refcount-based GC to close them:

- `coverage.py:37` — `open(os.path.abspath(__file__), encoding="utf-8").read()`
- `coverage.py:119` — `hosts = json.load(open(F.HOSTS, encoding="utf-8"))`
- `rosetta.py:54` — `open(os.path.abspath(__file__), encoding='utf-8').read()`
- `rosetta.py:349, 372-373, 389, 395` — several `json.load(open(...))` without `with`
- `pantheon.py:45` — `open(os.path.abspath(__file__), encoding="utf-8").read()`

None of these are a practical leak under CPython (the file is closed as soon as the temporary
object is garbage-collected, essentially immediately after `.read()`/`json.load()` returns), and
the self-integrity "bad control chars" checks in particular are one-shot startup checks, not
something called in a loop. Flagging per the audit checklist's explicit ask about resource leaks,
but this is a style nit rather than a functional defect.

**VERIFIED** (pattern present as described; practical impact assessed as negligible on CPython).

### L4 — rosetta.py:169-171 — outlier filter can discard a genuinely extreme character, not just parse noise

```python
# rosetta.py:166-171
if len(out) >= 8:
    med = sorted(out.values())[len(out) // 2]
    out = {k: v for k, v in out.items() if v <= med * 1000}
```

Documented and deliberate (see the comment immediately above), but worth naming explicitly per
the audit brief: this filters by *value*, not by rank/count, so it is not the kind of `[:N]`
roster cap Hard Rule 0 targets — it's a data-quality heuristic that could, in principle, also
discard a character whose native-scale value is legitimately >1000x the host wiki's median (some
franchises do publish figures that extreme for a single outlier character). **Judgment call, not
a violation** — flagging so the owner can confirm the 1000x threshold is the intended tradeoff.

### L5 — pantheon.py:265 — single-element tuple loop reads as vestigial generality

```python
# pantheon.py:265
for path in ("Z_FIGHTERS.json",):
```

Looping over a one-element tuple to merge exactly one file. Harmless, but it's a pattern that
usually exists because more paths were once (or are meant to be) in the list. Worth a glance to
confirm this isn't standing in for a merge that should include more rosters (e.g. any other
hand-built tier files this project may grow later) but was never filled in.

### L6 — Console-display truncation that is honestly labeled or backed by complete persisted data (judgment calls, not violations)

Per the audit brief's instruction to flag every cap and say whether it's a violation or a bound
on a display/sample — the following are all **display-only** caps where the full underlying data
is either persisted in full elsewhere or the omission is explicitly labeled, so none of these are
treated as Hard Rule 0 violations:

- `coverage.py:161, 166, 171` — `[:12]`, `[:show]` (default 26), `[:10]` on the three printed
  "sources with no host / worst covered / best covered" lists. The full per-source table is
  written to `data/COVERAGE.json` unsliced at line 182-183 — only the console summary is capped.
- `derivation.py:534` — `sorted(LEDGER, key=...)[:6]` on the printed "deepest derivation chains"
  report. `LEDGER` itself (112 hand-authored physics/math quantities, not catalogued content) is
  never sliced; this is a report display only.
- `rosetta.py:343` (`--probe`) and `rosetta.py:383` (`--refine` summary) — `[:6]`/`[:12]` on
  manual CLI diagnostic output. The `--refine` full result is written to `OUT` unsliced at line
  377-378 before the capped summary prints.
- `catalog.py:64-67` — `missing[:30]` in `cmd_stats`, with an explicit
  `"... and {len(missing) - 30} more"` line. This is the one case in the batch that actively
  discloses the truncation to the reader rather than letting it look like completeness, which is
  the specific harm Hard Rule 0 is written against.
- `build_terminal.py` and `render.py` — see CLEAN notes below; both have real per-entry roster
  loops (`nd.s.map(...)`, `ss.forEach`, `ws.forEach`, `containment_svg`'s `for i, ch in
  enumerate(children)`) that iterate every element with no `[:N]` cap. The only slicing present
  in either file trims individual **label strings** for on-screen legibility
  (`.slice(0,22)`, `[:26]`, etc.), with the full name preserved in the tooltip/panel text or in
  the underlying JSON — build_terminal.py even carries an explicit in-code comment (lines 52-54)
  documenting a *prior* cap-of-8 bug on the shelved-here roster that was deliberately fixed to be
  uncapped, and another (lines 108-114) about a prior all-49-entities-misgraded bug from a
  matching false positive, both showing the file's roster-completeness concerns have already had
  a dedicated pass.
- `render.py:222` (`WS.build_all(limit=1)`) and the `--write` block (lines 239-247) writing one
  sample SVG per DRAWN tier — this is `main()`'s own self-test/smoke-test path ("every tier
  viewable"), not the real per-address rendering pipeline (that's the `view()` function itself,
  called elsewhere in the project outside this file, with a real coordinate per call). Not a cap
  on catalogued output.

---

## CLEAN

- **catalog.py** — CLEAN. Read-only query tool; no writes, no swallowed exceptions, no roster
  caps beyond the one explicitly-labeled console summary noted in L6.
- **derivation.py** — CLEAN. Ran the module directly (`C:/Users/imarl/miniconda3/python.exe
  derivation.py`): the 112-quantity ledger closes with no dangling parents, no rootless
  derivations, no cycles, and the module performs no file writes at all, so there's no two-writer
  surface. The one `except SyntaxError` in `scan_constants()` is correctly narrow and logs via
  `silence.note` rather than swallowing broadly. Only note is the display-only `[:6]` at L6.
- **build_terminal.py** — CLEAN on Hard Rule 0 specifically: every roster/entry-list iteration in
  the JS template (shelved-here sources, worlds on the valence, ring labels) is unsliced; only
  individual label strings are character-trimmed for legibility, with full text preserved in
  tooltips and the panel. The Python `main()` writes the complete `NAVTREE.json` payload into the
  HTML unsliced, with a documented, correct `<` -> `\u003c` neutralization to prevent a
  catalogue-name from prematurely closing the inline `<script>` block. No other findings.

---

## Notes on scope

- I did not have grounds to inspect `data/SEVENFOLD.json`'s actual contents, so M4's collision
  risk in `render.py` is verified as a code pattern but unverified as a currently-live bug.
- `assay.py`, `feats.py`, `pipeline.py`, `silence.py`, `worldseed.py`, `address_space.py`, and
  `Z_FIGHTERS.json`'s schema are outside this batch; several findings above (M3, M5) reference
  them only to establish that a referenced name/file is absent/undefined, not to audit their own
  internals.
