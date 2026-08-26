# SWEEP 34 — BATCH 09 AUDIT

Modules read end to end: `magnitude.py` (1114), `silence.py` (521), `identity.py` (423),
`prose_gate.py` (347), `sevenfold.py` (274), `cleanup.py` (227), `catalogue_aurora.py` (184),
`scope.py` (152).

Nothing under `src/` was modified. `state/HALT.json` was not touched. `prose_gate.py` was read
only; its one finding is filed to OWNER and is a report, not a request to change anything.

Every finding below was re-derived from the source or measured against the data on disk. Where a
claim needed a measurement, the measurement is quoted.

---

## magnitude.py

### FINDING M1 — guard 3 ("the entity must be the DOER") never looks at the entity. MAJOR

The module docstring, lines 32-34:

```
  3. SUBJECT      the entity must be the DOER. Reuses the patient-check that pipeline.py
                  already applies to scale notes, plus a check that another named actor is not
                  standing between the entity and the verb.
```

The implementation, line 335 and lines 391-395:

```python
def verify(entity, got, ev):
    """Apply guards 1-4. Returns (scores, worksheet, rejections)."""
...
        # 3 SUBJECT -- the entity has to be the doer.
        if P._PATIENT.search(text) or _HANDOFF.search(text):
```

`entity` is never read in `verify`. AST-verified:

```
src/magnitude.py verify args= ['entity', 'got', 'ev'] UNUSED= ['entity'] lineno 335
```

Neither operand is entity-aware. `pipeline._PATIENT` (pipeline.py:1038) is a generic passive-voice
pattern (`\b(?:must be|to be|can be|was|were|is|are|been|being)\s+...`), and `_HANDOFF`
(magnitude.py:196-199) requires only `\b[A-Z][a-z]+\b` — *any* capitalised word — between the
handoff verb and `who|which|then`. So the guard tests the sentence's grammar, never who the entity
is. The incident the docstring cites ("Goku summoned Zeno, who ... erased the rogue Kai") is caught
by accident of shape, and the reverse case — the entity genuinely being the doer in a sentence that
contains any handoff clause — is rejected for the wrong reason. The unused parameter is the proof
the check was designed to use the entity and does not.

### FINDING M2 — `_split_assay` silently drops slices whose transport failed. MAJOR

Lines 476-499:

```python
        while i < len(rows):
            block, size = [], 0
            ...
            got = _ask(c, SYSTEM, prompt, AXIS_SCHEMA)
            if not got:
                continue
```

A slice whose call fails is skipped with no record and no mark on the sheet. The axis's score then
comes from whichever slices happened to answer, and nothing downstream can tell a score computed
over 10 slices from one computed over 1. The function's own docstring, lines 459-462, promises the
opposite: "Every candidate sentence is still read: each axis's list is sent in SPLIT_SLICE-sized
slices, an axis's score is the best-evidenced slice's answer". This is the module's own stated
failure mode — a partial record wearing a complete result's clothes — inside the function written
to avoid truncation.

### FINDING M3 — the charter regression exits 0 when one benchmark of six reproduces. MAJOR

`calibrate()` returns a count, lines 899-901:

```python
    print(f"anchor band reproduced on {band_hits}/{len(BENCHMARKS)} published assays")
    _land(rows, len(rows) == len(BENCHMARKS))
    return band_hits
```

`main()`, lines 1100-1101:

```python
    if a.calibrate:
        return 0 if calibrate() else 1
```

`band_hits` is 0-6, so the process exits non-zero only when *no* benchmark reproduced its band. One
hit out of six is reported to any caller reading the exit status as a pass. The docstring calls this
function "the instrument's regression test".

### FINDING M4 — the printed charter reference value is wrong for two of six benchmarks. MINOR

Lines 866, 881 and 894 render the published decimal as `int(val % 1 * 100)`. Measured:

```
BENCH Jotaro 2.14 -> printed .14
BENCH Kenshiro 3.52 -> printed .52
BENCH Luffy 4.08 -> printed .08
BENCH Naruto 4.31 -> printed .30      <-- charter says 4.31
BENCH Goku 7.62 -> printed .62
BENCH Jace 2.88 -> printed .87        <-- charter says 2.88
```

Binary truncation, not a data error: `4.31 % 1` is `0.3100000000000005` and `2.88 % 1` is
`0.8799999999999999`, and `int()` floors. Display only — `row["published"]` stores the true value —
but the column a person compares against is the wrong number.

### FINDING M5 — stale `silence.note` tag pointing into a different function. MINOR

Line 235, in `quantity_scores`:

```python
        except (ValueError, KeyError):
            silence.note("magnitude.py:151")
```

The handler is at line 234. Line 151 is `nc = 4096 if len(prompt) + len(system) < 11000 else 8192`,
inside `_ask`. A failure ledger entry for a quantity-parse fault would send the reader 84 lines away
to unrelated code. (Tree-wide context: 71 of 75 numeric note tags no longer match their handler's
line, but the rest are off by one; this one is off by 84 and crosses a function boundary.)

### FINDING M6 — two hand-rolled tmp-and-replace writes where `silence.write_json` belongs. MINOR

`calibrate._land`, lines 848-850:

```python
        with open(_cr + ".tmp", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1, ensure_ascii=False)
        silence.replace_retry(_cr + ".tmp", _cr)
```

`run_batch.work`, lines 1055-1071, does the same for `ASSAYS.json` plus an inline copy of
`replace_retry`'s backoff loop. Both use a PID-less tmp name, which is precisely what
`silence.write_json`'s docstring says is now unavailable to get wrong ("THE TMP NAME CARRIES PID AND
THREAD ... Two writers of the same path otherwise collide on the temp file itself"). `_land`'s
`replace_retry` verdict is discarded, so a checkpoint that did not land reads as one that did.
`run_batch`'s copy is under a `threading.Lock`, which protects it inside one process only.

---

## silence.py

### FINDING S1 — `instrument()` and `_handlers()` use different definitions of "silent", and the rewriting one is the loose one. MAJOR

`_handlers`, lines 132-134 (the version fixed today — asks the BODY):

```python
        body = "".join(ast.dump(stmt) for stmt in node.body)
        records = any(t in body for t in ("health", "record", "log", "print", "raise",
                                          "swallow", "silence", "LEDGER"))
```

`instrument`, lines 482-484 (still asks the WHOLE HANDLER, and drops `silence` from the tokens):

```python
            if any(t in ast.dump(node) for t in ("health", "record", "log", "print",
                                                 "raise", "swallow", "note", "LEDGER")):
                continue
```

Two consequences, both measured over `src/`:

* Because `"silence"` is missing from `instrument`'s tuple, **50 handlers that `audit()` reports as
  observed would be rewritten by `--instrument`** — among them every handler carrying this project's
  documented exemption marker, e.g. `chain.py:141`, `chain.py:159`, `completeness.py:76`,
  `coverage.py:71`, `dashboard.py:536`, `gpu_lane.py:375`, `runguard.py:64`, `sweep.py:90`, whose
  bodies open with `_ = "silence-exempt: ..."`. The convention that keeps deliberate silences
  documented is invisible to the tool that would overwrite them.
* `ast.dump(node)` serialises the exception TYPE and the bound name as well as the body — the exact
  tautology the comment at lines 127-131 says was removed one node up. Currently latent (measured:
  0 handlers in `src/` are skipped by `instrument` on a type-name match alone), but it is the same
  defect in the same module, one function away from the one that was fixed.

### FINDING S2 — the module docstring's handler count is off by an order of magnitude. MINOR

Line 25:

```
are 45 such handlers in this tree, and that number is the real bug; the fifteen were its output.
```

Measured with the module's own instrument, today:

```
handlers total 612
silent 143
```

The number the file names as "the real bug" is not the number its own audit produces.

---

## identity.py

### FINDING I1 — branching alone cannot admit a continuity, though two docstrings say it can. MAJOR

Module docstring, lines 57-60:

```
Population is sufficient but not necessary and branching is sufficient but not necessary --
`(Revelation)` shares no bearers yet and is obviously a continuity, while `(Fates)` has one
bearer and is obviously a continuity because that bearer exists in three other branches. Either
alone admits it.
```

`_is_continuity` docstring, lines 193-196, repeats it: "`(Revelation)` shares no bearers yet and is
still plainly a continuity, so branching cannot be required -- only sufficient."

The code, lines 205-207:

```python
    if n >= MIN_BEARERS:
        return True
    return n >= 2 and shared >= max(2, 0.5 * n)
```

A designator with one bearer returns False no matter how many other branches that bearer appears
in — the `(Fates)` case the docstring uses as its worked example is refused. And at `n == 2`,
`max(2, 1.0)` is `2`, so *both* bearers must be shared; "most of whose bearers" (line 190) is
actually "all of them" at the only count where the rule can fire. The failure direction is the one
the module calls unrecoverable (lines 96-98: "a wrong merge is not").

### FINDING I2 — `load()` hand-rolls the cache write. MINOR

Lines 218-223:

```python
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    tmp = CACHE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(inv, f, indent=1, sort_keys=True)
    silence.replace_retry(tmp, CACHE)
    return inv
```

`DESIGNATORS.json` is a shared `data/` file. The tmp name carries no pid or thread, so two
concurrent `identity.py --refresh` runs write the same temp path; and `replace_retry`'s verdict is
thrown away, so `load()` returns the fresh inventory whether or not it reached disk.
`silence.write_json` covers both.

### FINDING I3 — three top-level definitions sit after the `__main__` guard. MINOR

Line 374-375:

```python
if __name__ == "__main__":
    sys.exit(main())
```

`EPOCH_REQUIRED` (391), `epoch_directive` (407) and `epoch_acceptable` (418) are defined below it.
Run as a script, the interpreter reaches `sys.exit(main())` before those statements execute, so the
epoch mandate does not exist in that process. `main()` happens not to need them today; every caller
that does (`magnitude.py:609`, `:670`, `:705`, `verify_math.py:1008-1017`) imports the module, so
this is latent rather than live — but it is a loaded gun aimed at an owner-ruled safety.

---

## prose_gate.py — READ ONLY

This module was read and not touched. The one finding is filed to OWNER as a report. `prose_enabled`
and `step4_enabled` are treated here as what they are: the owner's hold, correctly fail-closed
(strict `is not True`, re-read per call, unreadable config refuses). Layers 1, 2, 3 and 4b were
checked and do what their docstrings say.

### FINDING P1 — the "entries the manifest never asked for" penalty never reaches the verdict. MAJOR

`section_shortfall`, lines 246-253, adds the extra-entry complaint to `missing` but adds nothing to
`required`:

```python
    # AND SO MUST AN ENTRY NOBODY ASKED FOR. `max(0, ...)` floored the ghost term at zero, so a
    # model returning MORE entries than the manifest requested paid nothing -- padding with
    # invented or duplicated entities was free, and Hard Rule 1 forbids exactly that.
    extra = max(0, len(blocks) - expected_entries)
    if extra:
        missing.append("%d entr%s the manifest never asked for -- an invented entry is a "
```

`assert_block_complete`, lines 259-269, decides only on the ratio:

```python
    present, required, missing = section_shortfall(text, expected_entries)
    ...
    frac = present / required
    if frac < (1.0 - SECTION_LOSS_FLOOR):
        raise ProseRefused(
```

A well-formed extra entry contributes equally to `present` and `required` inside the loop, so it
moves `frac` not at all. Reproduced against the live module (three complete entries, manifest asked
for two):

```
blocks=3 expected=2 -> present 15 required 15 frac 1.0
missing: ['1 entry the manifest never asked for -- an invented entry is a fabricated record, not a bonus']
assert_block_complete DID NOT REFUSE, returned frac = 1.0
```

`generate.py:304` is the only production consumer and it calls `assert_block_complete`, so padding is
still free — the comment describes a fix that landed in the message and not in the verdict.

The companion drill cannot see it. `drill.py:222-225`:

```python
    net(a, "entries the manifest never asked for are refused",
        lambda: any("never asked for" in m
                    for m in PG.section_shortfall(good + good + good, 2)[2]),
        "AUDIT DEFEAT 3: max(0, ...) floored the ghost term, so padding was free")
```

It asserts the *string* appears in `missing`. It is green, and the thing it is named for does not
happen. `verify_math.py` §19s checks `section_shortfall`/`assert_block_complete` on the ghost and
loss cases but not on this one.

This is a report for the owner, per the batch's standing instruction. Nothing here was changed.

---

## sevenfold.py

### FINDING V1 — `shelve()` is degenerate when weights are equal, and `build()` always calls it that way for worlds. MAJOR

`shelve`'s docstring, lines 100-104:

```
    Balance is by construction: the ordered list is cut into `span` contiguous blocks at each
    level, so no branch can swell into the giant component that wrecked every discovered scheme.
```

`seams`, lines 121-129, cuts at the weakest gaps:

```python
        gaps = []
        for i in range(len(block) - 1):
            a, b = block[i], block[i + 1]
            gaps.append((weights.get((a, b), weights.get((b, a), 0.0)), i))
        gaps.sort()
        k = max(1, min(span, len(block)))
        return sorted(i for _, i in gaps[:k - 1])
```

When every gap has the same weight, `gaps.sort()` breaks the tie on the index, so `gaps[:k-1]`
selects positions 0..k-2 — the first six seams — producing six one-member children and one holding
everything else. Measured against the live module:

```
empty-weights depth2, 100 members, children of root: [(0,1),(1,1),(2,1),(3,1),(4,1),(5,1),(6,94)]
depth5 root children:                                [(0,1),(1,1),(2,1),(3,1),(4,1),(5,1),(6,94)]
```

`build()` takes that path for every source's worlds, line 204:

```python
        inner = shelve(names, {}, depth=len(WORLD_TIERS))
```

`weights` is `{}`, so `affinity_order` is skipped (`shelve` line 105 falls to `sorted(members)`) and
every gap is 0.0. The multiverse and universe tiers are therefore built exactly as the giant
component the module docstring says the design exists to prevent. The `main()` balance table would
print `1-N` for those tiers, which reads as the intended range rather than as the collapse.

### FINDING V2 — the printed occupancy divides sources by the universe-tier capacity. MINOR

Lines 221-223:

```python
    print(f"\nsources shelved : {len(coords)}")
    print(f"capacity        : {CAPACITY:,} universe slots ({SPAN}^{len(TIERS)})")
    print(f"occupancy       : {len(coords)/CAPACITY:.2%}  — sparse by design")
```

`CAPACITY` is `SPAN ** len(TIERS)` = 16,807 universe slots, but `coords` holds sources, and sources
occupy the top three tiers only — 343 slots, as line 170 states (`SOURCE_TIERS = (...)  # 7^3 = 343
slots for 209 sources`) and as `build()`'s docstring argues at length. The printed figure understates
source occupancy by a factor of 49 and then labels the result "sparse by design".

---

## cleanup.py

### FINDING C1 — the eaten-escape guard carries an inert entry and skips the list that actually needs it. MINOR

Lines 85-92:

```python
for _n, _p in (("_NAV", _NAV), ("_EMPTY_MECHANIC", _EMPTY_MECHANIC),
               ("_SETTING_META", None)):
    if _p is not None and any(ord(c) < 32 for c in _p.pattern):
        raise SystemExit(f"{_n} contains a control character; the escape was mangled in transit")
```

`_SETTING_META` is not defined in this module; it lives at `pipeline.py:1094`. The tuple entry is
`None` and the `if` skips it, so one third of the guard's roster is a name that checks nothing, in a
guard whose whole argument is that a pattern which cannot match "reports zero violations and looks
like success".

Meanwhile `_MARKUP` (lines 63-73) is not covered, and its first pattern is
`re.compile(r"\s*\bWP\b(?=\s*[\(,]|\s*$)")` — a word-boundary escape, the exact shape the guard
exists to catch. If that one arrived mangled, `clean_description` would strip nothing and report
zero markup fixes.

`_NAV`'s split anchoring (`$` on one half of the alternation, `\b` on the other) was checked and is
deliberate and correct; the comment at lines 45-58 already records the run-33 misreading, and the
two halves genuinely differ for the reason given.

---

## catalogue_aurora.py

### FINDING A1 — the docstring's element count does not match the files on disk. MINOR

Lines 9-11:

```
  1. Richer. The codex's "Full Contents" manifest lists element NAMES only; the XML carries a
     full <description> for each. Dr. Firestorm's + The Elements Beyond alone yield 1,159
     elements from the XML against 123 names from the codex.
```

Measured today by running the module's own `parse_folder` against the owner's custom directory:

```
drfirestorm 425 the-elements-beyond 681 sum 1106
```

1,106, not 1,159. The claim is the argument for this module superseding `catalogue_codex.py`, so the
number is load-bearing prose.

The write-verdict discipline at lines 148-165 was checked and is correct — `write_record_catalogue`
is gated, and the `written` roster is built from landed writes only. The roll write two lines later
is not; see W1.

---

## scope.py

### FINDING X1 — the scope signal is drawn from a truncated ranked list. MAJOR

Lines 73-83:

```python
    for q in QUERIES:
        d = F.api(host, {"action": "query", "list": "search", "srlimit": "3", "srsearch": q})
        ...
    pages = F.fetch(host, titles[:8])
    text = " ".join(F.strip_wikitext(v) for v in pages.values())
    counts = {lab: len(rx.findall(text)) for lab, rx, _ in _RE}
```

`titles` is accumulated in wiki search-relevance order across four queries, and `titles[:8]` drops
everything past the eighth. `srlimit: 3` caps each query's contribution before that. Both are
internal fixed numbers, not a `--limit` a person set. The output of this truncation is
`MIN_MENTIONS`-thresholded raw counts, so the decision it feeds is directly sensitive to how much
text was read: a fiction whose universe-scale material sits on the ninth-ranked page is measured as
though that page does not exist, and the result is written to `SCOPE.json` as that fiction's
Magnitude ceiling — which `magnitude.host_ceiling` then uses to clamp every entity in it. Hard Rule
0's own wording: a cap on an ordered listing "silently decides that everything past the cutoff does
not exist".

Recurrence: `handoff/sweep24/AUDIT_batch06.md:320` reported this same `titles[:8]` cap. It is still
in the source, unchanged.

### FINDING X2 — `build()` takes a `records` argument it never uses, and `main()` computes it. MINOR

Line 102 and line 143:

```python
def build(records, hosts):
```
```python
        out = build(P.records(), hosts)
```

AST-verified:

```
src/scope.py build args= ['records', 'hosts'] UNUSED= ['records'] lineno 102
```

`P.records()` walks the whole 216-file record tree on every `--build`, and the result is discarded
at the callee's first line.

### FINDING X3 — `ceiling_for()` has no callers. MINOR (curatorial — OWNER)

Line 123. `grep -rn "ceiling_for" src/ docs/ *.md` returns exactly one hit: its own `def`. The live
path to the same data is `magnitude.host_ceiling` (magnitude.py:942), which reads `SCOPE.json`
directly and does its own live-probe fallback. Filed to OWNER because it is a public function and
deleting one is a curatorial call, not a repair.

Recurrence: reported at `handoff/sweep26/AUDIT_batch07.md:250` and noted again in sweeps 23, 30 and
32. Sweep 32's note ("used by `magnitude.py`/`pipeline.py` per the code's own comment") is not borne
out by grep — neither module calls it. Still present and still uncalled, which is why it is filed to
OWNER for a decision rather than reported once more.

---

## cross-module

### FINDING W1 — `silence.write_json`'s verdict is discarded, then success is printed. MINOR

Three sites in this batch:

* `catalogue_aurora.py:170-172` — the roll write, immediately after 18 lines of comment explaining
  why write verdicts must be gated. `main()` then prints `Wrote {len(written)} records from Aurora
  XML` regardless.
* `scope.py:118-119` — `SCOPE.json`; `main()` prints `{got}/{len(out)} wikis scoped  ->  {OUT}`.
* `sevenfold.py:266-269` — `SEVENFOLD.json`; the next statement is `print(f"\nwrote {p}")`.

`write_json` returns `replace_retry(tmp, path)` (silence.py:383) and its docstring says so:
"Returns True if the file landed. Never raises on a denied replace". A denied rename therefore
prints as a completed write in all three. Tree-wide this is 37 of 48 call sites; the three above are
the ones in this batch, and `catalogue_aurora`'s is the one whose module already argues the
opposite.

---

## QUESTIONS (not filed as orders)

1. **`prose_gate.MIN_ENTRY_BODY_CHARS` / `SECTION_LOSS_FLOOR` are owner-set constants.** No question
   about their values; only confirming they are read as owner settings and were left alone.
2. **`magnitude._split_gate` (line 580) accepts any citation that is a substring of a candidate,
   with no length floor**: `any(ft in o for o in own)`. A three-character `feat` would pass. The
   one-shot path's equivalent (`verify`, line 377-378) requires either containment *or*
   `_overlap > 0.6`, and rejects an empty citation explicitly (run #27's fix). Is the split path
   deliberately looser, or should it carry the same floor? No live instance found.
3. **`magnitude.assay_entity` line 679** coerces an out-of-ladder anchor to `"M0"`:
   `anchor = got.get("anchor") if got.get("anchor") in A.LADDER else "M0"`. The split path defers
   instead (`_split_assay` returns None at line 516-517 when the anchor is not in `A.LADDER`). Is
   the one-shot silent coercion intended, or should it defer like its sibling?
4. **`magnitude.candidates(ev, cap=None)`** — no caller anywhere passes `cap` (`magnitude.py:595`,
   `sweep.py:166` both call `candidates(ev)`). Keep as a Hard-Rule-0 tripwire, or remove?
5. **`silence.write_json` leaves its tmp behind when `replace_retry` gives up** (lines 372-383, no
   cleanup on the False path). No orphans exist on disk today (`find data state -name "*.tmp"` → 0),
   so this is theoretical. Worth a `finally`, or deliberate so the content survives for inspection?
6. **`silence.py`'s "WHAT THIS FILE DOES" (lines 34-40)** lists only `swallow(kind)` and `audit()`.
   The module is now also the project's atomic-write layer (`write_json`, `replace_retry`,
   `replace_if_unchanged`, `digest_of`, `append_line`) and half its length. Should the header say so?
7. **`silence._ensure_import`** detects an existing import by alias name only
   (`any(getattr(a, "name", "") == "silence" ...)`, line 447), so `from silence import note` would
   not be recognised and a duplicate `import silence` would be spliced in. Harmless today; no such
   import exists in `src/`.
8. **`sevenfold.shelve` lines 147-149** — `while len(coords[m]) < depth: coords[m].append(0)` is
   unreachable: `split` descends to `depth` for every non-empty chunk, so every member already
   carries exactly `depth` coordinates (verified: `all(len(v) == 5 ...)` is True). Defensive padding
   to keep, or dead?
9. **`sevenfold.py` says "209 sources"** at lines 170, 176 and 183. `data/SWEEP_ROLL.json` currently
   holds 215 rows and `data/records/` holds 216 files. Stale, or is 209 a deliberate historical
   reference to the run that produced the shape?
10. **`sevenfold` line 245** — `ok = "OK" if hi <= SPAN else "OVER SPAN"` is a check that cannot
    fail, and the comment above it says so and explains why it is kept. Recorded as reviewed and
    deliberately left; not a finding.
11. **`cleanup.clean_ceiling` lines 128-131** — `if len(low_pref) >= 1: return min(low_pref, key=len)`.
    The comment argues prefix matching is safe because "a name cannot prefix an unrelated entry by
    accident", which is an argument about the *unambiguous* case; with several prefix matches the
    shortest is chosen silently. Was `>= 1` meant to be `== 1`?
12. **`cleanup.py` never clears `thin_description`** (line 189). An entry whose description later
    grows past `_THIN` keeps the flag. Intended as a permanent provenance mark, or should it be
    re-evaluated on each pass?
13. **Note-tag convention.** 71 of 75 numeric `silence.note("file.py:NNN")` tags across `src/` no
    longer match their handler's `lineno`; most are off by one and point at the guarded statement
    instead (`catalogue_aurora.py:76` tags `:74` for a handler at 75; `scope.py:112` tags `:110` for
    a handler at 111). Only `magnitude.py:235` is badly wrong (filed as M5). Is the intended anchor
    the `except` line — as `silence.instrument` writes it (line 493) — or the failing statement? A
    ruling would make the whole set fixable mechanically.
