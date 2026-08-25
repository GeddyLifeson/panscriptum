# Batch 09 — run33
Modules read: magnitude.py (1109 lines), handbuilt.py (487 lines), tiers.py (360 lines),
scout.py (287 lines), genre.py (247 lines), profile.py (201 lines), physics.py (149 lines)

## FINDINGS

### 1. magnitude.py:114-116, 921 — NOT_AN_ENTITY's disambiguation clause never matches  [severity: MAJOR]
The regex is built to reject two kinds of junk pages before they enter the assay queue: list/
category/index pages (anchored at `^`) and disambiguation pages (anchored at `$`):

```python
NOT_AN_ENTITY = re.compile(
    r"^(list of|category:|template:|index of|timeline of|glossary|gallery\b)|"
    r"\(disambiguation\)$", re.I)
```

`queue()` applies it with `re.match()`:
```python
if NOT_AN_ENTITY.match(r["name"]):
```
`re.match` only tries a match starting at position 0. Because the `^` in the pattern binds only
to the first alternative, the second alternative `\(disambiguation\)$` is unanchored on its own
— but `match()`'s implicit start-at-0 constraint means it can still only succeed if the *entire*
string equals `"(disambiguation)"`. Verified directly:

```
>>> NOT_AN_ENTITY.match("Kirby (disambiguation)")   -> None   (should reject, does not)
>>> NOT_AN_ENTITY.search("Kirby (disambiguation)")  -> matches
>>> NOT_AN_ENTITY.match("List of Pokemon")          -> matches (this half still works)
```
So the "list of / category: / index of / ..." branch works as intended, but the disambiguation
branch — one of the two junk-page classes the docstring at line 110-113 explicitly calls out —
never fires for any real disambiguation page title. `handbuilt.py`'s own "Molecule Man" entry
(line 208-209) independently documents that `'Molecule Man'` is exactly such a stub page that
the automation has to route around by hand, which is consistent with this filter silently
letting these pages reach the assay queue instead of excluding them. The project's own
independent check suite (`verify_math.py:1034-1036`) tests only the "list of" branch against
this same regex and never exercises the disambiguation case, which is why the gap was not
caught. Fix is either `re.search` in `queue()`, or anchoring the second alternative with its own
`^.*` / restructuring the group so `match()` anchoring doesn't defeat it.

### 2. Five `silence.note()` calls carry stale line-number tags instead of the project's own descriptive convention  [severity: MINOR]
`silence.note(site)` feeds a persistent failure ledger (`health.record(f"silent:{site}", ...)`,
see `silence.py:330-348`) that the project explicitly built to make silent failures traceable —
this is the exact machinery Hard Rule -1 in `CLAUDE.md` and this file's own `_BAD_CHARS` guard
exist to support. Every call site in this batch except five uses a stable descriptive tag (e.g.
`"magnitude.py:pool_ready"`, `"scout.py:verify-http"`) that survives edits. Five sites instead
hard-coded a line number at authoring time, and edits above them since have made every one of
those numbers wrong:

| call site (current line) | tag string | actual code moved to |
|---|---|---|
| `magnitude.py:235` | `"magnitude.py:151"` | off by 84 lines |
| `tiers.py:247` | `"tiers.py:245"` | off by 2 lines |
| `scout.py:259` | `"scout.py:241"` | off by 18 lines |
| `profile.py:132` | `"profile.py:131"` | off by 1 line |
| `profile.py:137` | `"profile.py:135"` | off by 2 lines |

None of these tags now identify their own call site. Anyone triaging `state/failures.json` (or
grepping for `silent:magnitude.py:151`) is pointed at the wrong code. This is exactly the kind
of drift the project's own tooling (`liveness.py`, `drill.py`) is built to catch in the
*structure* of a guard; here the guard fires correctly but its self-identification is wrong —
contract drift in the diagnostic, not the check itself.

### 3. profile.py:52 — the B32 alphabet doesn't implement what its own comment claims  [severity: MINOR]
```python
B32 = "0123456789abcdefghjkmnpqrstuvwxyz"      # Crockford-style: no i, l, o, u
```
This string is 33 characters, not 32, and `u` is present at index 27 — the comment's claim that
`u` is excluded is false. Real Crockford Base32 excludes exactly `i, l, o, u` to leave 32 symbols
(the point of excluding `u` specifically is to avoid the alphabet spelling words it shouldn't).
Verified: `len(B32) == 33`, and the only letters actually missing from a-z are `i, l, o`.

Currently inert: `_b32()` (used for the address field) masks with `n & 31`, which can only ever
select `B32[0:32]` — the orphaned 33rd character (`'z'`, at index 32) is never produced, so
address round-tripping through `_b32`/`_unb32` is unaffected. The feature field (`f = ...` in
`encode()`) indexes `B32` directly by a table position rather than by bitmask, but every table in
`worldseed.py` (`LANDFORM`, `CLIMATE`, `CONDITION`, `TECH`) has 3-6 entries, far short of the 33rd
slot, so that path is unaffected today too. But the alphabet is not actually Crockford Base32 as
documented, `decode()`'s `_unb32`/`tbl[B32.index(ch)]` would silently accept the extra symbol if
it were ever produced, and any future feature table that grows past 32 options would hit
`IndexError` on decode with no guard.

### 4. physics.py:111-125 — sphere_volume/binding_energy have no boundary guard for radius<=0, unlike every sibling formula in the file  [severity: MINOR]
```python
def sphere_volume(radius_m):
    return 4.0 / 3.0 * math.pi * float(radius_m) ** 3

def binding_energy(mass_kg, radius_m):
    ...
    G = 6.67430e-11
    return 3.0 * G * float(mass_kg) ** 2 / (5.0 * float(radius_m))
```
`joules_for()` two functions above explicitly raises `KeyError` on an unknown material or mode
"rather than defaulting to rock... A silent default here would be a wrong energy wearing the
shape of a right one" — the file's own stated philosophy for this exact class of input error.
`sphere_volume`/`binding_energy` don't apply it to their own inputs: `radius_m <= 0` isn't
validated. `radius_m == 0` in `binding_energy` raises a bare unhandled `ZeroDivisionError`
instead of a clear domain error; a negative radius silently returns a negative volume/energy
(the cube preserves sign) rather than being rejected, which would propagate a wrong-signed
number into `assay.axis_score` without any indication anything was wrong. (`kinetic()` in the
same file, by contrast, was checked computationally and is safe: no double `v < C` can make the
relativistic branch divide by zero, since IEEE-754 rounding never takes `v/C` to exactly 1.0 for
`v` strictly less than `C`.) I could not confirm from this batch alone whether any live caller
(`anchors.py`, not in this batch) ever derives a zero or negative radius; flagging on the code as
written, which has no guard where its sibling function does.

### 5. magnitude.py:524-549 — compose()'s budget round-robin branch is unreachable in the current codebase  [severity: INFO / dead code]
`compose(entity, cand, epoch, budget, head_note=None)` has a whole round-robin evidence-budgeting
branch (`if budget: ...`) with real logic (interleave axes so a fixed character budget doesn't
starve later-declared axes). Searched the full `src/` tree: `compose(` is called exactly once,
at `magnitude.py:610`, always with the literal `None` for `budget`. No other module imports or
calls it with a truthy value. The branch is therefore dead in practice today. This looks
deliberate — `assay_entity`'s return dict comments `"evidence_dropped_to_fit": dropped,  # always
0 now; kept so a future budget cannot be silent"` — so it reads as intentionally-retained
capability rather than an oversight; reporting per the brief's instruction to report dead code
regardless of apparent intent.

### 6. scout.py:77, 174-179 — MIN_NAME_HITS=2 can never be satisfied for a source with fewer than two usable catalogued names  [severity: MINOR]
```python
MIN_NAME_HITS = 2
...
sample = [n for n in names if n and len(n) > 3][:PROBE_NAMES]
```
`verify()` accepts a proposed page only if `hits >= MIN_NAME_HITS` (2). `hostless()` only
requires a source to have *some* entries (`r.get("entries")` truthy) before it's handed to
`scout()`, so a source cataloguing a single named entity (or several entities all <=3 characters
long, which are filtered out before counting) produces a `sample` of length 0 or 1. For such a
source, no page — including the correct one — can ever score 2 name-hits, so `scout()` will
report "none" for it on every run, forever, regardless of transport or model quality. This is
the mirror image of the "no citation given" bug magnitude.py's own comment calls out (run #27) —
a check that cannot pass for a class of legitimate input, rather than a check that cannot fail.

## QUESTIONS

### A. Does the model's cited "feat" reliably come back as `[N] <verbatim text>`, or sometimes as a bare number?
`magnitude.py`'s SYSTEM prompt (line ~299-301) instructs: "Cite, for each axis, the exact feat
number that justifies it," and `compose()` labels each candidate `[1]`, `[2]`, ... specifically
for that purpose (line 555-559). But `verify()`'s guard 1 (VERBATIM, line 372-382) treats the
returned `feat` string purely as free text to normalize and substring/overlap-match against the
mined feats' own sentences — it never looks up a numeric index directly. Separately, the
cross-axis-citation check at line 718-723 regexes the *raw* model output for a `\[(\d+)\]` prefix,
which only makes sense if the model's citation does begin with a bracket number followed by the
restated text. If the model ever returns a *bare* number (e.g. `"3"`) without the sentence, guard
1's `cn in t` substring check (line 378) could spuriously succeed against any mined feat whose
text happens to contain that digit anywhere (page numbers, "3,000 kili", dates) — exactly the
class of degenerate-citation loophole the file's own "run #27" comment (line 356-371) fixed for
*empty* citations, but a single short digit isn't caught by that `if not cn` guard. I can't tell
from this batch alone whether the model in practice always restates the text (making this
theoretical) or sometimes returns a bare number (making it live). Settling it: log a sample of
real `got["axes"][ax]["feat"]` values from a live or recent run and check whether any are shorter
than, say, 15 characters or purely numeric.

### B. Is guard 4 (saturation) meant to fire on instrument-measured axes, not just model-scored ones?
In `assay_entity` (magnitude.py:728-735), `quantity_scores()` overwrites up to two axes (ruin,
reach) with arithmetically-derived scores *before* `saturated(scores)` is evaluated. `saturated`'s
own docstring frames it as catching "a sheet from a model that would not refuse" — but by the
time it runs, some of the scores it inspects may be instrument readings, not model opinions. With
only two axes quantity-scorable, this can't trigger saturation by itself (needs 6 of 11 at
ceiling), but it can contribute to crossing that threshold for an otherwise-legitimate
heavily-measured entity. Worth confirming whether that's intended, since the guard's own
justification text doesn't account for it.

### C. `magnitude.py:937-965` `host_ceiling`'s module-level `_SCOPE_CACHE` dict is written from
worker threads in `run_batch` without a lock. Dict writes are atomic in CPython so this can't
corrupt the structure, but two threads racing on the same uncached host will both perform the
(possibly network-hitting) `SCOPE.scope_for(host)` call redundantly. Given this exact file
already documents one prior incident from an unlocked shared-state check (`pool_ready()`'s
docstring, line 120-126, "ten workers racing the same probe drove the answer to False
permanently"), it's worth confirming this second one is judged safe rather than merely unnoticed
— it doesn't produce wrong results today, only duplicate work.

## CLEAN
- **handbuilt.py** — read in full. Static, hand-curated assay data plus a report generator; no
  bugs found. The write-then-print ordering fix (line 444-465) and its rationale check out
  against the code as written.
- **genre.py** — read in full. Classifier, cue tables, and `classify_source`'s `cap` refusal all
  check out; the `Counter`-based ranking handles the zero-score / tie case correctly.
- **tiers.py** — read in full aside from the stale-tag note in Finding 2. Cut thresholds, nesting
  asserts, complete-linkage vs single-linkage split, and the hyperverse pooling logic in
  `xenoverse_grounding` all check out against their own stated design.
