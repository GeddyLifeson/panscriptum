# run39 — AUDIT batch 04

Modules owned (obtained from `sweep_plan.batches(16)[3]["modules"]`, not from any typed list):

    standards.py          2,175 lines
    derivation.py           715
    endpoint.py             561
    anchors.py              457
    sweep.py                344
    catalogue_models.py     301
    physics.py              246
                          -----
                          4,799 lines, all read in full, no sampling.

Every finding below was verified against the current source before it was written down, and
where the verification was a run rather than a read, the run is quoted. Read-only pass — no
source file was edited.

---

## MAJOR

### 1. `standards.py:1735-1751` — a runner probe that could not tell is published as "runner up", and HOLDS

`ollama_runner_up()` documents its own contract at `standards.py:130`: *"`None` means 'could
not tell' and is never reported as a fault."* The boolean honours that. The READING does not.

```
runner = ollama_runner_up()
_runner_holds = runner is not False
_runner_reading = (
    ("resident %s -- NO llama-server process" % ", ".join(...)) if runner is False
    else ("runner up, %d resident: %s" % (len(resident), ", ".join(...))))
```

There are three possible values and only two branches. Reproduced:

    True   holds=True  | runner up, 1 resident: qwen3:8b
    False  holds=False | resident qwen3:8b -- NO llama-server process
    None   holds=True  | runner up, 1 resident: qwen3:8b        <-- the probe never said this

`ollama_runner_up()` returns `None` whenever the `tasklist` spawn raises or exceeds its 25 s
timeout (`standards.py:142-143`) — an ordinary event on a machine that routinely runs fifteen
jobs plus a crawl, and the same ordinariness the `duplicates` handler at `standards.py:1917`
already argues for its own `Get-CimInstance`. So a HIGH standard prints an affirmative claim
about a process nobody looked at.

This sits inside the block whose own comment (`standards.py:1693-1711`) says *"UNMEASURED is a
reading; silence is not"* and *"UNMEASURED IS NOT GREEN"*, and whose sibling — the context
verdict at `standards.py:1783-1789` — gets it right: `ctx_verdict is None` sets
`_ctx_holds = False` and an explicit `"UNMEASURED -- ..."` reading. The two halves of one block
disagree on the file's own doctrine.

**Remedy:** give the third state its own branch. `runner is None` should emit
`_runner_holds = False` and a reading naming the probe failure ("UNMEASURED -- the
llama-server process probe did not answer (`tasklist` timed out or raised); see
state/failures.json for the class standards.py:ollama-runner"), matching the `_unaskable`
treatment already built four lines above at `standards.py:1714-1720`. If the owner prefers
`None` to keep holding (so no remedy fires on absent evidence, as the counters standard does at
`standards.py:1317`), then the READING must still say "could not tell" rather than "runner up"
— the two cannot both be silently merged into the affirmative.

### 2. `standards.py:1370` — Hard Rule 0: source names cut mid-name on the standard that exists to name them

```
worst = sorted(good, key=lambda c: c.get("coverage", 0))
detail = "; ".join("%s %.1f%%" % (str(c["source"])[:18], 100 * c.get("coverage", 0))
                   for c in worst)
```

The comment four lines above (`standards.py:1364-1368`) is emphatic that the row cap was
removed — *"ALL OF THEM, WORST FIRST -- not `[:3]` ... it silently decided which sources
'count'"* — and the per-name character cut survived that repair. There is no `…` marker and no
"and N more"; an eighteen-character prefix is presented as the source's name.

This is the `observed` field of `every source is fully catalogued`, a HIGH standard whose order
text tells the reader to run `catalogue_web --recatalogue --shortfall 100` on the named
sources. Real roll names exceed eighteen characters routinely (`Lost Mines of Phandelver` is
24, and the order text itself names it), and prefixes collide: anything of the form
`Warhammer Fantasy *` folds onto one string. The file has already fixed this exact shape twice
elsewhere and said so — `standards.py:1671` ("ALL OF THEM, not `[:120]` characters -- that cut
the joined name list mid-name") and `standards.py:1742` ("EVERY RESIDENT NAME, not
`resident[0][:28]` ... ranking is allowed here, truncating is not").

**Remedy:** drop the `[:18]` and print `c["source"]` whole. The list is already ordered
worst-first, which is the ranking Hard Rule 0 permits; nothing after this field needs
alignment.

### 3. `derivation.py:685-694` — `check_graph()` reports a CYCLE and then `main()` never returns

`check_graph()` detects cycles correctly (`derivation.py:490-503`). `main()` prints the
problems and **does not stop** (`derivation.py:662-669` has no early return), then walks each
quantity's deepest chain:

```
while [p for p in LEDGER[cur]["parents"] if p in LEDGER]:
    chain.append(cur)
    cur = max((p for p in LEDGER[cur]["parents"] if p in LEDGER), key=depth)
chain.append(cur)
```

There is no visited set and no bound, so on a cyclic ledger this loop runs forever. Verified by
injecting a two-node cycle into a live import:

    problems: ['CYCLE     zz_a -> zz_b -> zz_a']
    LOOPED: chain walk did not terminate after 50 steps

`depth()` does not save it — its own `seen` guard makes `depth(a)=2, depth(b)=1` for a 2-cycle,
so `max(..., key=depth)` picks a parent every time and the walk oscillates.

The consequence is that the one fault this module exists to name is the one fault it cannot
report: the VERDICT line at `derivation.py:709` is never reached, `main()` never returns its
exit code, and any caller judging this module by return code (it is run as a script, and
`allsweep` judges modules by rc) sees a TIMEOUT rather than `N FAILURES`.

**Remedy:** either return early — `if problems: print VERDICT; return 1` before the chain
panel — or bound the walk with a visited set (`while ... and cur not in chain`). The early
return is the smaller change and matches what the panel is for: the chain map is evidence for
`depth()`'s argument, which is meaningless over a ledger that does not close.

---

## MINOR

### 4. `standards.py:604` — `[:40]` on the per-provider reason, in the function whose docstring says nothing is capped

```
names = sorted("%s (%s)" % (r.get("provider") or "?",
                            str(r.get("error") or "no model list")[:40])
               for r in rows if not r.get("models"))
```

`provider_pool_denominator`'s docstring says at `standards.py:576`: *"NOTHING IS CAPPED --
every unverified provider is named."* Every provider **is** named; its REASON is cut at 40
characters with no marker. This is the legacy branch (a snapshot predating
`catalogue_models`' `counts` block), and it is the branch where the error string is the only
surviving evidence — the branch's own comment (`standards.py:596-599`) says exactly that: *"the
derived figure cannot tell `no key` from `the provider refused`: only the fixed sweep records
that."*

`catalogue_models.py:130-138` removed the identical cut on the identical string one module
upstream under order 6d354a508b96, with the reasoning *"a URL plus a status line already passes
70 characters, so the cut was landing on the reason itself"*. Forty is tighter than the seventy
that was found too short.

**Remedy:** drop the `[:40]`; collapse whitespace instead (`" ".join(str(...).split())`), the
way `catalogue_models.py:138` does, so the row stays one console line without losing text.

### 5. `standards.py:172` — `str(exc)[:80]` on the failure phrase the token-flow standard prints verbatim

`_flow_failure()`'s fallback branch cuts the exception text at 80 characters. That string
becomes `secs`, which `standards.py:1839` prints as the entire `observed` of the HIGH standard
`the local model produces tokens`, and the order text at `standards.py:1841-1845` tells the
reader to *"Read the detail before acting"* because the remedy differs per cause. This is the
branch reached when the exception is NOT a timeout, NOT a `ConnectionRefusedError` and carries
no `code` or `reason` — i.e. the unclassified case, where the raw text is all there is. No
marker is printed.

**Remedy:** `" ".join(str(exc).split())` uncut, as in finding 4.

### 6. `standards.py:1274` and `:1261` — `CHARTER_REGRESSION_MAX_AGE_H` restated as a literal "26h"

`CHARTER_REGRESSION_MAX_AGE_H = 26` at `standards.py:516`; the floor string at
`standards.py:1274` reads `"every scored reference overlaps its published interval, within
26h"`, and the comment at `standards.py:1261` says `"A file older than 26h"`. Both are
hand-copied. Every other floor in `check()` is interpolated (`f"{MAX_SWEEP_AGE_H}h"`,
`f"{MAX_PUBLISH_AGE_H}h"`, `f"{MAX_COVERAGE_AGE_H}h"`, `f"{MIN_DISK_GB} GB"`), so this is the
one that drifts silently if the constant moves.

Note this does NOT trip the module's own `every declared floor is measured` self-check: the
constant appears twice in comment-stripped code (its declaration at 516 and its use inside
`charter_regression_verdict` at 550), which is exactly the two occurrences that check requires.
Verified — I ran the self-check's own regex over the current file and it reports `dead: []`
over 28 declared floors. The self-check is working; a restated literal is simply outside what
it can see.

**Remedy:** `f"every scored reference overlaps its published interval, within
{CHARTER_REGRESSION_MAX_AGE_H}h"`.

### 7. `sweep.py:291` — Hard Rule 0: character name and source name cut in DEEPEST EVIDENCE

```
print(f"   {r['axes']:>4}{r['quantities']:>5}{r['chars']:>10,}   "
      f"{r['name'][:29]:<30}{r['source'][:25]:<26}{nat}")
```

The long comment immediately below (`sweep.py:293-305`) removed the `most_common(10)` /
`most_common(8)` caps and states *"The source name is no longer cut either"* — that sentence is
about the two lists BELOW it (BIGGEST GAPS, REACHED BUT SILENT), and it is true there. It is
not true here, twelve lines above it, and the same paragraph explicitly reprieves this table
only for its ROW cap: *"`DEEPEST EVIDENCE` above keeps its `[:top]` -- that is an explicit
--top request for the best N and is documented as such."* The per-value cuts were not
considered. The `source` column here is not the last column (`native` follows it), so the
alignment argument the paragraph makes for the other lists does apply — but a cut with no
marker still reads as the whole name.

**Remedy:** either widen and mark (`r['name'][:29] + "…"` when longer), or move `native` before
the two name columns and let them run whole, which is what the same comment did for the lists
below.

### 8. `sweep.py:84` — stale cross-reference: `load()`'s "only call site (`:129`)" is neither

The docstring reads *"The only call site (`:129`) asks for the evidence of every Person-category
entry ... and does no existence check first"*. Verified against the current file:

* `sweep.py:129` is a comment line inside `rosetta_index` (*"A character graded on more than one
  scale keeps the finer-grained one"*), not a call.
* `sweep.load` has **no caller anywhere**. `grep` over `src/` for `sweep.load` / `from sweep
  import` returns only `verify_math.py` (which drives it as a test subject) and prose mentions.
  The evidence read that actually runs inside `sweep.sweep()` is `cachekey.load(F.CACHE, host,
  e["name"], ...)` at `sweep.py:181` — a different function in a different module.

`verify_math.py:4004-4019` already diagnoses this and is explicit that the callerless half is
filed as order `2b695c192470`, and that *"`sweep.load`'s own docstring repeats the same `:129`
claim, which is that file's to correct, not this one's."* It has not been corrected. The
docstring's substantive argument (an absent cache is the normal case, a corrupt one is a
finding) is still correct and worth keeping; only the citation and the "only call site" claim
are false.

**Remedy:** replace *"The only call site (`:129`)"* with a symbol-level statement of the same
contract — e.g. *"The caller this exists for asks for the evidence of every Person-category
entry and does no existence check first; the live path today is `cachekey.load` inside
`sweep()`, and `load` itself currently has no caller (order 2b695c192470)."* Cite by symbol,
not by line, per order a09a0e003c31.

### 9. `anchors.py:246-247` — stale cross-references: both `assay.py` line numbers have drifted

The comment cites *"no worksheet (assay.py:886, honesty theorem H5)"* and *"'no axis scored
from cited feats; band-only' (assay.py:897)"*. Verified against the current `assay.py`:

* `assay.py:886` — a docstring line about `calibration_report`'s sigma sweep. The H5
  no-worksheet return is at `assay.py:899-902`.
* `assay.py:897` — `_check_weights(weights)`. The band-only return carrying
  `"reason": "no axis scored from cited feats; band-only"` is at `assay.py:911-913`.

Both are off by 13-16 lines. The substantive claim they support — that `assay.assay` has two
documented paths returning `decimal: None`, and that only the second is reachable from this
file — remains true, and the guard the comment justifies (`isinstance(dec, bool) or not
isinstance(dec, (int, float))` at `anchors.py:261`) is correct as written.

**Remedy:** cite the two returns by symbol and reason string rather than by line number, as
order a09a0e003c31 established.

### 10. `endpoint.py:389` — stale cross-reference: `feats.py:1367` is a blank line

The comment reads *"`feats.py` reads a source bound `pages:<source>` in WIKI_HOSTS.json through
`source_pages`/`fetch_html` (feats.py:346, :1367)"*. Verified:

* `EP.fetch_html` is called at `feats.py:1363`. `feats.py:1367` is **blank** (confirmed with
  `sed -n '1367p' | cat -A` → `$`).
* `EP.source_pages` is called at `feats.py:348`; `:346` is the `host.startswith("pages:")` test
  two lines earlier — close, but not the call the sentence names. (There is a second
  `EP.source_pages` call at `feats.py:1450`, which the citation does not mention.)

The rest of that paragraph is accurate and load-bearing: `MODE_HTML` at `endpoint.py:394`
genuinely has no reader, `detect()` genuinely cannot return it, and that is already recorded as
order a60c150b6303.

**Remedy:** cite by symbol (`feats.source_pages` / `feats.fetch_html`) and drop the line
numbers.

### 11. `anchors.py:190-209` — the COLLEGE reading and the bit value are computed for every anchor and graded by nothing

`run()` calls `custodes.convene(...)` and `rigor.measure_bit_value(...)` once per anchor and
prints `interval`, `prior_divergence_share`, `attestation_floor_share` and the bit value. No
`verdict(...)` reads any of them, and the five entries in `CLAIMS` (`anchors.py:336-370`) take
`col` as a parameter that no lambda body uses. This file's own `__main__` comment
(`anchors.py:440`) is *"A CHECK WHOSE RESULT IS PRINTED AND DISCARDED CANNOT FAIL"*, and the
comment at `anchors.py:266-275` claims the file was repaired so that *"EVERY INVARIANT THIS
FILE GRADES ... CAN FAIL"* — which is true of what it grades, and leaves two whole
sub-instruments exercised at five calibration points and unjudged.

I checked the obvious candidate before filing this and it is NOT the right assertion:
`custodes.convene`'s `covers_every_reading` is documented at `custodes.py:540-543` as *"a
GUARANTEE being published, not a check being run ... true by construction for every possible
input and cannot fail"*. Grading that would add a tautology, which is the opposite of the
repair.

**Remedy (a judgement, hence SESSION):** decide which properties of the college reading are
falsifiable at a fixed anchor and grade those. Candidates that can actually fail:
`0 < interval` and `interval` finite for every anchor; `prior_divergence_share +
attestation_floor_share == 1.0` within rounding; `dispersive_without_mechanism == []` (a
Custos the table marks dispersive but whose widening has no derived mechanism is a real,
reachable state `custodes.py` gives its own key to); and `measure_bit_value(band)` strictly
increasing across `A.LADDER`, which is the claim its own docstring makes and which nothing
currently tests at anchor level.

---

## INFO

### 12. `physics.py:50-51` — `HERE` bound and never read; the `sys.path.insert` beside it is unused

`HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` at `physics.py:50` has no
reader anywhere in the file (grep confirms one occurrence outside the module docstring). The
`sys.path.insert(0, ...)` on the next line is likewise inert — `physics.py` imports only
`argparse`, `math`, `os` and `sys`, and no module in this repo's tree depends on `physics`
having mutated `sys.path`. Both are boilerplate carried in from the modules that do need them.

Harmless today, but `physics.py` is the module the project created specifically because
constants had drifted away from their readers, so a constant with no reader in it is worth
retiring rather than leaving as a pattern to copy.

### 13. `endpoint.py:358-362` — `--list` claims to show everything and prints only three modes

```
for mode in (MODE_API, MODE_RAW, MODE_DEAD):
    rows = by.get(mode) or []
```

`by` is built by `by.setdefault(d["mode"], []).append(...)` over every row in the cache, so a
mode key that is not one of those three is collected and then never printed, with no residual
count. `--list`'s own help string is *"show everything already known"*.

In practice `detect()` can only write those three, so nothing is lost today — but `MODE_HTML`
exists as a named constant in the same file, `ENDPOINTS.json` is hand-editable and is merged
across processes, and a mode added to `detect()` without being added to this tuple would
vanish from the only listing there is. Cheap fix: iterate `sorted(by)` with the three known
modes first, or print a trailing count of rows in unrecognised modes.

### 14. `catalogue_models.py:161` — `LAST_WRITE_LANDED = True` is an affirmative default for a write nobody attempted

The module-level flag initialises to `True`. Its docstring is careful about the contract ("One
writer, one reader (`main`), one call"), and in the CLI path `sweep()` always runs before
`main()` reads it, so this is latent rather than live. But the value states that the last write
landed, and until `sweep()` runs, no write has been attempted — an importer that reads
`catalogue_models.LAST_WRITE_LANDED` without calling `sweep()` (or after a `sweep()` that
raised before line 279) is told the snapshot is current. `foreman.recatalogue_models` reads the
subprocess return code rather than this flag, so nothing is misled today.

`None` would be the honest initial value ("no write has been attempted"), with `main()`
returning non-zero for both `False` and `None`.

---

## QUESTIONS — two defensible readings each, filed here rather than as orders

**Q1. `anchors.py` CLAIMS 4 and 5 test hand-written constants against hand-written constants.**
Goku's claim is graded by `isinstance(a["scores"].get("volition"), (int, float))` where
`volition=9.4` is a literal twelve lines above in the same file; Yggdrasil's by
`a["scores"].get("volition") == A.UNESTIMABLE`, likewise a literal. Neither exercises `assay`,
`custodes` or `physics`. Read one way these are not instrument checks at all — they are
`ANCHORS`-edit guards, and the section comment's *"EVERY INVARIANT THIS FILE GRADES ... CAN
FAIL"* is true only in the sense that someone could edit the constant. Read the other way, a
guard on the calibration inputs is exactly what an anchoring file should have, since silently
changing a reference's declared volition would invalidate every reading below it. I do not
think this should be changed without a ruling on which of the two it is meant to be.

**Q2. `anchors.py:337-344` — the ceiling-saturation verdict is close to automatic.**
`INSTRUMENT_WINDOWS["M10"] == (30, 30)`, so `lo + (s/10)*span` returns 30 for *any* numeric
score, and all eleven M10 scores are hardcoded numerics. The verdict can therefore only fail if
the WINDOW table changes or a score becomes a sentinel — it cannot detect a wrong score, which
is what its note ("every faculty pins at 30 regardless of score") reads as testing. That said,
detecting a window-table regression is a real job and the `transcendence_grade == "V"` half is
genuinely falsifiable. The file already flags the zero-width window itself as an OWNER QUESTION
at `anchors.py:427-435`, so this is arguably already surfaced.

**Q3. `anchors.py:342` — `str(v).startswith("30")` instead of `== 30`.** A prefix test on a
number. It cannot false-pass today, because `assay.instrument` bounds every faculty with
`max(1, min(30, ...))` at `assay.py:1187`, so 30 is the only value whose string starts "30";
and the test must be a string test because at M10 the grade is present and faculties are
formatted `"30 (Grade V)"`. Correct as written, fragile in shape. Left unfiled.

**Q4. `catalogue_models.py:220-231` — `if r:` after `live.get(name)` cannot be false.**
`stale` rows are only appended inside the `else` branch where `r = live.get(name)` was truthy,
so every provider named in `stale` is in `live`. The guard is defensive rather than
tautological in intent, and removing it would make a future refactor crash rather than skip.
Not filed.

**Q5. `standards.py:1017-1021` — `probe failures (reported, not judged)` passes `True` as its
`holds`.** Deliberate and labelled, but it is counted in `report()`'s `N/N standards met` line
as a met standard, so the ratio is inflated by one guaranteed pass. Whether a
reported-not-judged row belongs in the denominator at all is a presentation question for the
owner, not a defect.

**Q6. `standards.py:828-830` vs `standards.py:1115` — two parsers for one field.** The
`feats per chunk` standard scrapes digits out of the `·`-delimited part containing "feats"
(`int("".join(c for c in part if c.isdigit()) or 0)`), while the fabrication standard uses a
regex (`_re.search(r"([\d,]+) feats", det)`) on the same `read["detail"]` string. The scrape
concatenates every digit in the part, so `"12 feats/5s"` would yield 125; the regex would yield
12. They agree on today's format. Two readers of one field in one file is the drift shape this
project files elsewhere, but nothing is currently wrong, so it is a question rather than a
finding.

---

## What was checked and found CORRECT (so the next sweep does not re-derive it)

* **`standards.py`'s own `every declared floor is measured` self-check works.** I ran its exact
  regex and word-boundary logic over the current file: 28 floors declared, `dead: []`. The
  fix that widened the pattern to `CHARTER_REGRESSION_MAX_AGE_H` and un-anchored `M(IN|AX)_`
  is holding.
* **`derivation.py`'s `SCAN_MODULES`** is derived from `os.listdir(HERE)` and no longer a
  hand-typed list; `_target_names` genuinely handles `Tuple`/`List`/`Starred` and
  `scan_constants_with_reason` genuinely handles `AnnAssign`.
* **`derivation.provenance()` is live** — four callers in `verify_math.py:377-384`.
* **`derivation.scan_constants()` (the thin wrapper at `:617`) has no caller in `src/`** other
  than nothing; `main()` uses `scan_constants_with_reason`. Its docstring says it is *"kept
  unchanged rather than widened because it is a public function with callers outside this
  file's control"* — that claim is false as of today. I did **not** file this: it is a
  deliberately-kept stable public signature, the docstring's reasoning (a caller that regains
  it must not break) is defensible, and it is documented in five previous sweep audits. If the
  owner wants the docstring softened to "no caller today; kept as the stable signature", that
  is a one-line comment edit, not a code change.
* **`anchors.py`'s `assay.py:1103` / `custodes.py:355,447` / `resonance.py:54` back-references
  to `anchors.py:186` and `anchors.py:190`** are all still accurate — 186 is the
  `A.instrument(...)` call, 190 is the `CU.convene(...)` call. The stale drift runs the other
  direction only.
* **`endpoint._save()` discarding its own return value at `endpoint.py:271`** is documented at
  `endpoint.py:122-125` as deliberate ("A refusal is NOT raised ... the hosts stay in `_DIRTY`
  and the next probe's save carries them"). Not a discarded verdict.
* **`custodes.convene()`'s `covers_every_reading`** is true by construction and correctly
  labelled as a published guarantee, not a check. `anchors.py` not reading it is right.
* **`physics.py`'s four domain guards** (`kinetic`, `joules_for`, `sphere_volume`,
  `binding_energy`) each refuse non-positive, NaN and infinite inputs on every parameter, in
  both the numerator and denominator positions. I looked for the asymmetry the comments
  describe (a guard on speed but not on mass, on volume but not on radius) and could not find a
  surviving one.
* **`standards.py`'s `shelf-ranks` `FileNotFoundError` branch** (`:1685-1686`) drops the
  standard without recording it in `_dropped` — which would be green-by-absence, except that
  `verify_math.py:6206` names this exact `silence-exempt: phase 7 has not run yet` case as the
  single documented exemption in the declared-vs-emitted reconciliation. Correct as built.
* **`sweep.nested_run()`** genuinely tests subset relations on member sets rather than counts,
  and `report()` draws only the longest genuinely nested run, printing everything else as
  separate populations with the crossover in both directions. The docstring's claim that
  nothing is hidden holds for the funnel; the only cut left in the file is finding 7.
