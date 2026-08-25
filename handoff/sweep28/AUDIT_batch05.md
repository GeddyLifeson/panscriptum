# Sweep 28 — Batch 05 audit

Modules: `src/read.py` (1136 lines), `src/silence.py` (426 lines), `src/worldseed.py` (328 lines),
`src/render.py` (253 lines), `src/profile.py` (202 lines), `src/physics.py` (150 lines).
Total: 6 modules, 2495 lines, all read in full, every line.

`NEXT_STEPS.md` §3 read first; each KNOWN item below was independently re-verified live against
current source, not assumed from the file.

---

## src/read.py

### [HIGH][NEW] `_names()`'s pronoun branch accepts ANY personal pronoun regardless of antecedent — it does not verify the pronoun refers to the queried entity

`src/read.py:188-190`
```python
    words = set(re.split(r'[^a-z]+', low))
    return bool(words & {'he', 'she', 'they', 'his', 'her', 'their', 'him',
                         'himself', 'herself', 'themselves'})
```
This is the second half of `_names(sentence, entity)` (defined `read.py:159`), whose docstring
promises "Is the entity actually the subject of this sentence?" and says it "[r]ejects the
generic subjects a techniques index uses." The name-match branch above it (`:182-183`) is
correctly tokenised. This branch is not: it returns `True` for **every** entity name whenever the
sentence contains any personal pronoun, with zero check that the pronoun's antecedent is the
entity being read. Reproduced directly:

```
>>> _names("Batman analyzed the debris field. He deduced the villain location from a "
...        "single fingerprint.", "Superman")
True
>>> _names(..., "Wonder Woman")
True
>>> _names(..., "Aquaman")
True
```
Same sentence, three different entities, all pass. Failure scenario: a shared/crossover page
(exactly the kind this file's own docstring already worries about — "MetalGarurumon then defeats
Azulongmon") is chunked and read once per entity. If the model returns a verbatim sentence about
a *different* named character on that page that happens to use a pronoun rather than the second
character's name, this guard lets it through as a feat of the entity currently being read. The
result is a feat silently misattributed between two catalogue entities sharing a page — the
project's signature "wrong result filed as a correct finding" defect, inside the one guard whose
job is specifically to prevent it.

### [MED][NEW] Chunk-selection membership test uses raw substring containment, not the tokenised match `_names()` was deliberately fixed to use

`src/read.py:635, 647-648`
```python
    keys = [w.lower() for w in re.split(r"[^A-Za-z0-9]+", name) if len(w) > 3] or [name.lower()]
    ...
            if own or any(k in ch.lower() for k in keys):
                density = sum(ch.lower().count(k) for k in keys)
```
`k in ch.lower()` is plain substring containment. `_names()` (same file, `:159-190`) has an
extensive docstring explaining exactly why this class of match is wrong and was replaced with a
word-boundary-start test — citing the real "GARURUMON"/"LOIS LANE via 'lane'" collisions found in
production. That fix was applied only inside `_names()`; the chunk-selection filter here, which
decides which pages/passages get *sent to the model at all* for a given entity, still uses the
unfixed substring form. Reproduced:
```
>>> keys = ['ares']   # entity "Ares"
>>> 'ares' in "the committee declares the outcome final and adjourns the session.".lower()
True
```
An entity like "Ares" pulls in any chunk containing "declares"/"prepares"/"compares" etc. Effect:
wasted model calls on irrelevant chunks (cost, and it feeds `density` which drives the chunk
read-order), and — combined with the `_names()` pronoun bug above — an irrelevant chunk pulled in
by a false substring hit can still produce a "verified" feat for the wrong entity if it contains
any pronoun.

### [HIGH][NEW] `read_entity`'s final record write and `_save_qcache` both use the exact fixed-name-tmp pattern this same file's `_chunk_put` was rewritten to fix

`src/read.py:756-757` (inside `read_entity`, the terminal per-entity JSON write):
```python
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    silence.replace_retry(tmp, path)
```
`src/read.py:876-879` (`_save_qcache`, the shared `state/read_queue_index.json`):
```python
        tmp = QCACHE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f)
        silence.replace_retry(tmp, QCACHE)
```
Both use a **fixed** temp filename. `_chunk_put` earlier in this very file (`:586-602`) carries a
long docstring explaining precisely why this is wrong and fixing it: *"A PER-WRITER TEMP NAME.
This was `p + '.tmp'`... two workers answering the same passage at once opened and truncated ONE
file — each writing over the other mid-dump, then both renaming it,"* and the fix is
`tmp = "%s.%d.%d.tmp" % (p, os.getpid(), threading.get_ident())`. That fix was not carried to
these two siblings 150-300 lines away in the same module. `replace_retry` makes the **rename**
atomic; nothing here makes the **write** safe, exactly the gap the `_chunk_put` docstring
describes. `read_entity`'s per-entity path is only at risk if the same entity is processed by two
concurrent `read.py` invocations (plausible: `--one HOST ENTITY` debug runs alongside a `--run`
pass), but `_save_qcache`'s target (`state/read_queue_index.json`) is touched by *every*
`read.py --run` invocation and has no such precondition — any two overlapping runs race on it.
`_save_qcache` additionally has no lock around its load→mutate→save cycle at all
(`_load_qcache()` at `:864-870`, mutation across `queue()`, `_save_qcache(qcache)` at `:964`), so
even with the tmp-name fixed this remains an unlocked cross-process read-modify-write: whichever
process's `_save_qcache` runs last silently discards the other's cache additions (data loss,
not corruption — the next run just re-derives the discarded entries at the cost of re-parsing).
This is the "grep the tree for the shape you just fixed" lesson (NEXT_STEPS lesson 14) applied to
one file against itself.

### [KNOWN][STILL OPEN] `cap_chunks` truncates before the ask loop; a capped entity is written to disk as a *complete* cache entry, and `chunks_skipped` conflates mention-filtered chunks with cap-excluded ones

`src/read.py:666-668, 737, 753-754`
```python
    chunks.sort()
    chunks = [(t, c) for _, _, t, c in chunks]
    if cap_chunks:
        chunks = chunks[:cap_chunks]
    skipped = sum(len(b) for b in text.values()) // size - len(chunks)
    ...
    "chunks_skipped": max(0, skipped),
    ...
    if unanswered:
        return out
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ... # writes the record as final/complete
```
Verified live against `NEXT_STEPS.md` §3's listed item (`read.py:605-760`). `cap_chunks` chunks
are removed from `chunks` **before** the read loop runs, so they never register in `unanswered`
(only chunks that were attempted and failed count there) — the `if unanswered: return out` guard
that exists specifically to stop a partially-read entity from being cached as final does not fire
for capped-out chunks, because they were never "unanswered," they were never tried. An entity read
with `--chunks N` is therefore filed permanently complete with only its first N (by density) chunks
ever read. `chunks_skipped` sums mention-filtered exclusions and cap-excluded chunks into one
number with no way to tell which is which. Default CLI (`--chunks` omitted) is uncapped, so this
requires an operator to pass `--chunks`, but the code path and the mis-marking are both still live.

---

## src/silence.py

### [KNOWN][STILL OPEN, reproduced] `uses_exc` is true whenever the handler names its exception variable, whether or not that name is ever used in the body

`src/silence.py:133-134`
```python
        uses_exc = bool(node.name) and node.name in body
        silent = not (records or uses_exc)
```
`body = ast.dump(node)` (line 127) is the AST dump of the *entire handler node*, which necessarily
contains the handler's own `name='e'` attribute as literal dumped text regardless of whether `e`
is referenced anywhere in the handler's body. Reproduced directly:
```
>>> src = "try:\n    x = 1\nexcept Exception as e:\n    pass\n"
records=False uses_exc=True silent=False
```
A genuinely silent `except Exception as e: pass` is marked "observed" purely because the variable
was named. This means the audit's own headline count of SILENT handlers systematically
undercounts every handler in the tree that happens to bind a name to its exception, which is most
of them by convention (`except Exception as e:`).

### [KNOWN][STILL OPEN, reproduced] `records` is a substring match against the whole AST dump, so any string literal or identifier that happens to contain one of the trigger words counts as "observed"

`src/silence.py:128-129`
```python
        records = any(t in body for t in ("health", "record", "log", "print", "raise",
                                          "swallow", "silence", "LEDGER"))
```
Reproduced directly: `except ValueError: y = "catalogue entry"` — a handler that does nothing
observable at all — is marked `records=True` because the string literal `"catalogue entry"`
contains "log" (`cata` + `log` + `ue`) as a substring, and that literal's text appears verbatim
inside `ast.dump(node)`. Any handler whose body merely assigns a string or names a variable
containing "log", "record", "print", etc. as a substring (e.g. a variable named `logbook_id`,
`printer_queue`, `record_id`) is misclassified as observed. Combined with the `uses_exc` bug
above, both halves of `silent = not (records or uses_exc)` are individually prone to false
positives on "observed," so `audit()`'s SILENT count is a floor, not a measurement — the true
number of unobserved swallows in the tree is higher than what `silence.py --dry-run`/`main()`
reports, and there is no way from the tool's own output to tell by how much.

### [KNOWN][STILL OPEN] `_handlers()` and `instrument()` each silently swallow their own AST-parse failures with no `silence.note()` call — inside the module whose entire purpose is banning exactly that

`src/silence.py:115-122` (`_handlers`):
```python
    try:
        with open(path, encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src)
    except Exception:
        return []
```
`src/silence.py:378-381` (`instrument`):
```python
        try:
            tree = ast.parse(original)
        except Exception:
            continue
```
Neither branch calls `silence.note()`, `print()`, `health.record()`, or anything else — both are
bare `except Exception: <drop the file>`, with no way to tell from `audit()`'s or `instrument()`'s
output that a file was skipped rather than clean. An unparseable module (a syntax error introduced
mid-edit, an encoding problem) silently vanishes from both the audit total and the instrumentation
pass, and the run reports as if every file in `src/` had been checked. This is the identical shape
the rest of the module exists to eliminate, unfixed in the module itself — confirmed unchanged
from the run #27 finding.

---

## src/worldseed.py

### [KNOWN][STILL OPEN] `--write` lands `data/WORLDSEEDS.json` via a raw `open(path, "w")` + `json.dump`, not `silence.write_json`/`replace_retry`

`src/worldseed.py:317-322`
```python
    if args.write:
        path = os.path.join(HERE, "data", "WORLDSEEDS.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({w["designation"]: {"address": address(w), **w} for w in worlds},
                      f, indent=2, ensure_ascii=False)
        print(f"\nwrote {path}")
```
Verified live against `NEXT_STEPS.md` §3's listed item. No temp file, no atomic rename — a reader
polling `data/WORLDSEEDS.json` mid-write (or a crash mid-write) sees a truncated/partial file, and
the two-writer contract (`silence.write_json` exists in this same tree specifically for this) is
bypassed. Unchanged from the prior finding.

No other findings in `worldseed.py` beyond the KNOWN item — `build_all()`'s two data-file reads
default to `{}`/`{}` on failure but both call `silence.note()` first (observed, not silent);
`_first()`'s seeded-fallback design and the full-description `WORLD` regex scan are both already
corrected per their own inline "Fixed 2026-08-24" notes and were re-verified present as described.

---

## src/render.py

### [MED][NEW, reproduced] `containment_svg()` displays "1 child" for a node with zero children

`src/render.py:110, 121-122`
```python
    n = max(1, len(children))
    ...
           f'{n} {"child" if n == 1 else "children"} &#183; span 1&#8211;7</text>']
```
`n` is computed as `max(1, len(children))` purely to keep the later angle-division loop
(`2 * math.pi * i / n`) from a divide-by-zero — but the same `n` is reused, unguarded, as the
*displayed child count text*. When `children` is genuinely empty, `n` reads `1`, and the SVG
prints "1 child" for a node that has zero. Reproduced directly:
```
>>> svg = containment_svg('universe', 'Some-Universe', [])
>>> re.search(r'>(\d+) (child|children)', svg).group(0)
'>1 child'
```
This is not a hypothetical edge case: `children_of()`'s own comment two functions above
(`render.py:169-175`) states plainly that `SEVENFOLD.json`'s deepest coordinate is `universe`, so
"`universe` has no charted children by either test" — i.e. `children_of("universe", ...)` returns
`[]` in the tree as currently shipped, and `main()`/`view()` calling `containment_svg("universe",
label, [])` on today's data produces a diagram whose header falsely claims "1 child &middot; span
1-7" for a leaf node. Every rendered "universe" tier diagram in the current tree carries this
wrong label.

No other findings in `render.py`. `children_of()`'s tier-gating (`:163-187`), `view()`'s dispatch
(`:190-205`), and the fetched-tier URL builders were all read and are correct.

---

## src/profile.py

### [HIGH][NEW] The "ROUND TRIP" self-test's own success condition is half-tautological and never checks most of what the profile string encodes

`src/profile.py:182-187` (in `main()`):
```python
    bad = 0
    for r in rows:
        d = decode(r["profile"])
        if d["address"] != r["address"] or d["profile"] != r["profile"]:
            bad += 1
    print(f"   {len(rows)-bad:,} of {len(rows):,} round-trip exactly   failures: {bad}")
```
printed under the banner `"ROUND TRIP — the string must reconstruct the world exactly"`
(`:179-181`). `decode()`'s return dict (`:94-112`) sets `"profile": profile` at line 111 —
literally the input parameter, echoed back unmodified:
```python
    return {
        "address": address,
        ...
        "profile": profile,
    }
```
So `d["profile"] != r["profile"]` compares `decode(x)["profile"]` (`== x` by construction, always)
against `x` — this half of the `or` can **never** evaluate `True`, for any input, ever. It is
exactly the "check that cannot fail" pattern (`NEXT_STEPS.md` lesson 9's `"" in t` case, same
shape). Worse: `decode()` also computes `genre`, `register`, `features` (four axes), `band`, and
`attested_axes` from the profile string — the majority of what the string is supposed to encode —
and **none of those five fields are compared back to the source values** (`genre`, `register`,
`w["features"]`, `w.get("band")`, `w.get("attested_axes")`) that `build_all()` fed into `encode()`.
The self-test's only live check is `d["address"] != r["address"]`. Failure scenario: introduce a
bug that swaps two entries in `AXES` ordering, or a collision in `GENRE_CODE`/`REG_CODE`, or an
off-by-one in the `BANDS` index lookup — anything that corrupts genre/register/feature/band
decoding while leaving the address bits untouched — and `main()` still prints
`"N of N round-trip exactly failures: 0"`, a clean bill of health for a self-test whose own banner
claims to verify the string "reconstruct[s] the world exactly."

### [MED][NEW, reproduced] The `B32` alphabet's own comment says it excludes `i, l, o, u`; the literal string includes `u`, and it is fully reachable (not dead code)

`src/profile.py:52`
```python
B32 = "0123456789abcdefghjkmnpqrstuvwxyz"      # Crockford-style: no i, l, o, u
```
Reproduced directly:
```
>>> len(B32)
33
>>> 'u' in B32, B32.index('u')
(True, 27)
>>> [c for c in 'ilou' if c in B32]
['u']
```
`i`, `l`, `o` are genuinely absent (comment correct on those); `u` is present at index 27. Because
`_b32()`/`_unb32()` (`:69-83`) mask/shift 5 bits per digit (`n & 31`, i.e. any value 0-31), index
27 is squarely inside the range the encoder can and does emit — `u` is not a theoretical/unreached
symbol, it is a normal, frequently-produced digit in real shelfmark addresses, directly
contradicting the inline claim. Standard Crockford Base32 is exactly 32 symbols (10 digits + 22
letters, excluding I L O U) for a clean 5-bit-per-character mapping; this alphabet has 33
characters, so its 33rd symbol (`z`, index 32) is the one that's actually unreachable by `_b32()`
(`n & 31` never produces 32) — meaning `decode()`'s regex-permissive address group
(`profile.py:95`, `[0-9a-z]+`) would accept a hand-edited or corrupted profile string containing
`z` in its address field and hand it to `_unb32()`, which calls `B32.index('z') == 32` and computes
`n = (n << 5) | 32` — a value that does not fit in the 5-bit-per-digit scheme the encoder actually
uses, silently producing an address integer no legitimate `_b32()` output could have encoded, with
no validation catching it. This second path requires a malformed input string rather than normal
operation, so it is secondary to the comment/code mismatch itself, but both stem from the same
uncorrected alphabet.

No other findings in `profile.py`. `encode()`/`decode()`'s AXES-order pairing, `galaxy_api()`, and
`build_all()`'s two data-file reads (both observed via `silence.note()` on failure) were read and
are otherwise correct.

---

## src/physics.py

Read in full, 150 lines. No correctness bugs, no swallowed failures, no caps, no two-writer
violations, no concurrency issues, and no comment/code contradictions found. This module is
deliberately strict: `kinetic()` raises rather than silently handling `v >= C`;
`joules_for()` raises on an unknown material or mode rather than defaulting to `"rock"`;
`binding_energy()`'s docstring explicitly states its own limitation (uniform-sphere approximation,
not to be used to set a band) and that limitation is honoured by the rest of the codebase per
`NEXT_STEPS.md`'s note that `assay.BAND_EDGES` uses the literature value for the Sun instead. No
findings to report for this module.

---

## Summary table

| Severity | Status | Location | Claim |
|---|---|---|---|
| HIGH | NEW | read.py:188-190 | `_names()` pronoun branch accepts any pronoun regardless of antecedent — feats can be misattributed between entities sharing a page |
| MED | NEW | read.py:635,647-648 | chunk-selection uses raw substring match, not the tokenised fix `_names()` already applies |
| HIGH | NEW | read.py:756-757, 876-879 | `read_entity` final write and `_save_qcache` both use fixed-name `.tmp`, the exact race `_chunk_put` in the same file was rewritten to fix; `_save_qcache` also has no lock around its cross-process RMW |
| KNOWN | STILL OPEN | read.py:666-668,737,753-754 | `cap_chunks` truncation caches a partial entity as complete; `chunks_skipped` conflates two causes |
| KNOWN | STILL OPEN | silence.py:133-134 | `uses_exc` true whenever handler names its exception, regardless of use — reproduced |
| KNOWN | STILL OPEN | silence.py:128-129 | `records` substring-matches whole AST dump — reproduced false positive on a string literal |
| KNOWN | STILL OPEN | silence.py:115-122,378-381 | `_handlers`/`instrument` silently drop unparseable files with no note(), inside the anti-silence module itself |
| KNOWN | STILL OPEN | worldseed.py:317-322 | `--write` uses raw open+json.dump, not `silence.write_json` |
| MED | NEW | render.py:110,121-122 | `containment_svg` shows "1 child" for 0 children — reproduced, live on today's `universe` tier data |
| HIGH | NEW | profile.py:182-187,111 | round-trip self-test's `d["profile"]!=r["profile"]` is tautologically False; genre/register/features/band never checked at all |
| MED | NEW | profile.py:52 | B32 alphabet comment claims "no u"; string includes reachable `u` at index 27 — reproduced |

batch05: 6 modules, 2495 lines read, 4 high, 4 med, 0 low, report at handoff/sweep28/AUDIT_batch05.md
