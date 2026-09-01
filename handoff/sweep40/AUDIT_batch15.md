# Sweep 40 — Batch 15 audit

Modules (read in full, line by line): `src/hostcheck.py` (1303 lines), `src/dashboard.py`
(1090 lines), `src/rosetta.py` (636 lines), `src/endpoint.py` (562 lines),
`src/axis_correlation.py` (404 lines), `src/feats_index.py` (370 lines), `src/resonance.py`
(299 lines), `src/chord_field.py` (211 lines).

## Overall impression

This batch is a mature, heavily-reviewed slice of the tree. Every one of these files carries
extensive "order <hash>" comments documenting prior fixes (compare-and-swap adoption for
`WIKI_HOSTS.json`/`ENDPOINTS.json`/`SOURCE_PAGES.json`, discarded-verdict gating, None-vs-zero
control-baseline fixes, Hard Rule 0 cap removals, Gauss-Seidel replacing a non-convergent Jacobi
sweep, etc.). Most candidate "findings" on first read turned out, on verification, to already be
fixed and narrated in past tense. Two genuine (but minor, cosmetic) defects survived
verification: stale `file.py:NNN` line-number citations inside comments, in the exact pattern
this project's own `dashboard.py` warns readers about. No fail-open, no discarded return value,
no un-gated read-modify-write, and no live Hard Rule 0 cap was found in this batch's actual
code paths.

## Findings

### 1. Stale cross-reference: `endpoint.py:389` cites `feats.py:346, :1367` — INFO — filed

**File:** `src/endpoint.py`, line 389 (inside the `MODE_HTML` block comment, lines 386-392):

```
# AND HTML MODE IS NOT A `detect()` VERDICT. Unlike MODE_API/MODE_RAW/MODE_DEAD, which `detect`
# earns by probing, this mode is SELECTED BY THE HOST PREFIX: `feats.py` reads a source bound
# `pages:<source>` in WIKI_HOSTS.json through `source_pages`/`fetch_html` (feats.py:346, :1367).
```

Verified against the current `src/feats.py`:

- `EP.source_pages(...)` is actually called at **feats.py:348** and **feats.py:1450**. Line 346
  is `if host and host.startswith("pages:"):` — the guard one line above the call, not the call
  itself.
- `EP.fetch_html(...)` is actually called at **feats.py:1363**. Line 1367 is a **blank line**
  between `_source_pages_text` and `evidence_for`.

The citation has drifted from the code it describes — the exact "a baked-in line number rots the
moment anything above it moves" failure `dashboard.py:77-80` documents in this same codebase.
No behavioural impact: both call sites are real, correct, and functioning as the comment
describes; the only cost is a reader who follows the citation to verify it landing on the wrong
lines (a guard clause and a blank line).

**Remedy:** update the citation to `feats.py:348, :1363`, or better, drop exact line numbers and
name the functions (`_source_pages_text`, the `pages:` branch in `reads_as_wiki`) the way
`dashboard.py`'s own `silence.note()` tags were moved to descriptive strings for this identical
reason.

**Filed:** `stale-xref-endpoint-feats-lines`, handler LOCAL, severity INFO.

### 2. Stale cross-reference: `dashboard.py:239` cites `standards.py:663` — INFO — filed

**File:** `src/dashboard.py`, line 239 (inside `_read_row`'s comment, lines 236-249):

```
# THE FABRICATION GUARD HAD NO INPUT, SO IT NEVER RAN ONCE. Run #28.
# `RE_READ` has captured `dropped` -- the count of model sentences the verbatim
# check REJECTED as not present in the source -- since the regex was written, and
# this dict threw it away one line after parsing it. `standards.py:663` then read
# `read.get("raw")`, a key NOTHING in the tree has ever set, ...
```

Verified against the current `src/standards.py`: line 663 today is inside the **"model calls per
hour"** standard's guidance text, unrelated to the fabrication guard. The actual fix this
comment narrates now lives at **`standards.py:1086-1122`** (`drop = read.get("dropped")`, the
`fab`/`why` computation, and the "sentences that survive the verbatim check" standard). Both
halves of the bug this comment describes are already fixed in both files — `dashboard.py` does
store `"dropped": _num(r["dropped"])` (line 250) and `standards.py` does read `job["dropped"]`
— so this is purely a historical narrative comment with a rotted line number, not a live defect.
It is, ironically, exactly the failure mode `dashboard.py`'s own `_num()` comment two hundred
lines earlier (lines 77-80) warns about for baked-in line-number tags.

**Remedy:** update the citation to `standards.py:~1086-1122`, or reference the standard by its
name (`"sentences that survive the verbatim check"`) instead of a line number.

**Filed:** `stale-xref-dashboard-standards-line`, handler LOCAL, severity INFO.

## Verified NOT findings (checked and cleared)

For completeness, these were the strongest candidates that turned out, on verification, to be
correct or already fixed:

- **`axis_correlation.py:380`** cites `dashboard.py:77-80` for "a baked-in line number rots the
  moment anything above it moves" — verified accurate; that quote is exactly what stands at
  those lines.
- **`feats_index.py:138`** cites `manifest_builder.py:342-358` for the "AND A FAILED LOOKUP SAYS
  SO, OUT LOUD" comment about a guarded `feats_for_source` call — verified accurate, word for
  word, at those exact lines in `manifest_builder.py`.
- **`resonance.py:54`** cites `anchors.py:190` as "the sole real caller of `convene()`" that
  "passes none" for `eta` — verified: `anchors.py:190` calls `CU.convene(a["anchor"],
  a["scores"], attestation=a["attestation"], worksheet="anchors.py")` with no `eta` argument.
  Accurate. (`resonance.py`'s wider claim — that `hodge_decompose`/`resonance_strength` have zero
  production callers — is itself an already-tracked, self-documented finding under order
  `f467f662be4b`; no new work order filed for it here to avoid duplicating that ticket.)
- **`RE_READ`/`RE_ROLL`** regexes in `dashboard.py` — checked against `read.py`'s and
  `feats.py`'s actual `print()` format strings (lines ~1243 of `read.py`, ~1673 of `feats.py`).
  Both still match; not stale.
- **`hostcheck.py`'s `_land_hosts`, `endpoint.py`'s `_save`/`register`, `feats_index.py`'s
  `host_to_sources`** — all implement genuine compare-and-swap via
  `silence.replace_if_unchanged`/digest-before-read, with the write verdict correctly threaded
  back to the caller and printed (not swallowed). No RMW-without-CAS hazard found in this batch.
- **`axis_correlation.py`'s `--top` cap, `feats_index.py`'s `feats_for_source` ranking,
  `dashboard.py`'s `watch()`/`safety()` "ALL open findings"/"EVERY breached net" lists** — all
  explicitly uncapped per Hard Rule 0, with the removed caps narrated in comments (2026-08-24 /
  order `50c9f6130b95` / order `89fc2eaf23f1`). `hostcheck.py`'s `PROBE=40`/`sample=12`-style
  limits are statistical measurement sample sizes for the fitness *test*, not truncations of a
  stored roster/output list, and are consistent with the file's own stated cost/budget reasoning.
- **`chord_field.py`** — pure constants/formulas module (Kerr self-focusing, Landauer floor,
  recoil momentum); all three formulas check out against their standard forms, and the removed
  dead `G_NEWTON`/`HBAR` constants are in fact absent and the surviving `C_LIGHT`/`K_BOLTZMANN`
  are in fact both used (`recoil_momentum`, `landauer_floor`).
- **`hostcheck.score()`'s verdict ladder and lift-vs-rate discipline**, **`rosetta.py`'s
  host-scoped `assays_by_host`/`check()` join** — both read correctly against their own
  docstrings; the historical raw-rate and unscoped-join bugs they narrate are visibly fixed in
  the current code (tuple-shaped `(lift, rate, host)` comparisons throughout; `by_host.get(host,
  {})` scoping in `check()`).

## Work orders filed

| code | where | handler | severity |
|---|---|---|---|
| `stale-xref-endpoint-feats-lines` | `src/endpoint.py:389` | LOCAL | INFO |
| `stale-xref-dashboard-standards-line` | `src/dashboard.py:239` | LOCAL | INFO |

## Coverage recorded

`sweep_plan.record('run40', [hostcheck.py, dashboard.py, rosetta.py, endpoint.py,
axis_correlation.py, feats_index.py, resonance.py, chord_field.py], batch=15)` — done.
