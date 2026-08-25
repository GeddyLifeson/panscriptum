# AUDIT — sweep30, batch 12

Scope: `src/rigor.py`, `src/chain.py`, `src/custodes.py`, `src/address.py`, `src/render.py`,
`src/chord_field.py`, `src/cachekey.py`. Every line read top to bottom in each file. Additional
tree-wide greps performed per the special focus on `cachekey.py` (M23) and on dead-code claims in
`custodes.py`/`rigor.py`. No secrets found in any of the seven files.

Severity counts: **HIGH 5, MED 6, LOW 4** (15 findings total).

---

## 1. `src/cachekey.py` — SPECIAL FOCUS: the M23 entity-cache-collision defect

### 1.1 The documented collision is real and REPRODUCED on the exact names in scope

`cachekey.py:51` — `_SANITISE = re.compile(r"[^A-Za-z0-9]+")`, applied by `name_stem()` (line 61-63)
before an 80-char cap. Reproduced directly against `src/cachekey.py` (miniconda python, scratch
dir, no repo state touched):

```
'Ten-Towns' -> Ten_Towns      'Ten Towns' -> Ten_Towns      COLLIDE: True
'Vár'       -> V_r            'Vör'       -> V_r            COLLIDE: True
'Magic 8 Ball' -> Magic_8_Ball   'Magic 8-Ball' -> Magic_8_Ball   COLLIDE: True
```
`natural_path()` returns byte-identical paths for each pair, exactly as the module's own docstring
claims. **REPRODUCED**, not a hypothesis.

### 1.2 The `cachekey.py` fix itself (`load`/`write_path`/`owns`) is correctly implemented, including under NTFS case-folding — REPRODUCED, clean

Built a scratch cache dir and drove `write_path` → `load` for both `Ten-Towns`/`Ten Towns` and for
a same-punctuation, case-only NTFS-folding pair (`Tag Der Toten` vs `Tag der Toten`, referenced in
`read.py:614-623`'s own comment as a second real collision class: NTFS folds
`Tag_Der_Toten.json`/`Tag_der_Toten.json` to one physical file even though `name_stem()` returns
two different Python strings). In both cases: the second entity's `write_path()` correctly detects
the natural slot is held by a different `entity` and returns the hash-suffixed sibling; `load()`
for each name then returns its own document, never the other's. This works specifically because
`write_path`/`load` do real filesystem I/O (`os.path.exists`, `open`) rather than Python string
comparison, so NTFS case-insensitive resolution doesn't defeat it. No bug found in `cachekey.py`'s
own logic. **Clean.**

### 1.3 HIGH — `read.py:queue()` builds its own raw entity-cache path and bypasses `cachekey` entirely — the exact M23 defect, still live, one call site away from the "fixed" `read_entity()` — REPRODUCED

`read.py:937-938` (outside this batch, found via the tree-wide grep the task required):
```python
path = os.path.join(FF.CACHE, re.sub(r"[^A-Za-z0-9]+", "_", h)[:40],
                    re.sub(r"[^A-Za-z0-9]+", "_", e["name"])[:80] + ".json")
```
This is the *same* raw four-site formula `cachekey.py`'s own docstring says was replaced
everywhere, hand-inlined again, with **no `cachekey.owns()` check** — unlike `read_entity()`
40 lines below it (`read.py:614-640`), which was given a documented "SECOND PASS" fix for this
exact defect (see its comment citing `Tag Der Toten` vs `Tag der Toten`). `queue()` opens whatever
file sits at the collision path and folds its `chars`, `axes`, `quantities` into the priority
ranking (`read.py:940-983`) with no ownership check — a colliding neighbour's mined-evidence
volume pollutes which entity the pipeline reads next, and the `qcache` memo (keyed on the shared
physical `path`, `read.py:952`) is then written/overwritten alternately by both colliding
entities on every run. This is read-time cross-contamination of the exact kind M23 was about,
in a call site the fix's own tree-wide sweep missed. **Fix**: route `queue()`'s path build through
`cachekey.load()`/`cachekey.candidate_paths()` the same way `read_entity()` was fixed to.

### 1.4 LOW — `hostcheck.py:711` still spells the sanitiser inline instead of calling `cachekey.host_dir()`

`hostcheck.py:711`: `d = os.path.join(HERE, "data", base, re.sub(r"[^A-Za-z0-9]+", "_", mined)[:40])`.
This builds a *host*-level purge directory (not a per-entity path — every entity cache under that
host is deleted as a unit), so it carries no collision risk itself, but it is functionally
identical to `cachekey.host_dir()` and violates the module's own stated principle 3 ("ONE HELPER,
NOT FOUR SPELLINGS... four independent copies of one convention is four chances for the next edit
to drift"). **Fix**: call `cachekey.host_dir(mined)` instead of re-deriving it.

### 1.5 No other undiscovered raw entity-path builders found

Tree-wide grep for the `re.sub(r"[^A-Za-z0-9]+", ...)` shape and its lowercase variants across all
of `src/` confirms every other site that builds a *per-entity* cache path (`coverage.py`,
`feats.py`, `pipeline.py`, `sweep.py`, `drill.py`, `prose_gate.py`, `hostcheck.py:799`) already
imports and calls `cachekey.load`/`write_path`/`candidate_paths`/`owns` correctly. `generate.py:62`
and other `[^A-Za-z0-9]+` hits are unrelated output-filename slugs, not entity cache keys.

---

## 2. `src/custodes.py` — the ten-Custos college

### 2.1 HIGH — `_ATT_BASE` is a hand-copied literal matching a DEAD function, not "DERIVED from `assay()`'s own attestation table" as the comment claims — REPRODUCED

`custodes.py:221-234`:
```python
# DERIVED from assay()'s own attestation table rather than restated. ...
_ATT_BASE = {"Witnessed": 0.10, "Instrumented": 0.08, "Transcribed": 0.20,
             "Reconstructed": 0.40, "Disputed": 0.55}
```
`assay.py:819-856` defines `interval_from_hands()`, which has **zero callers anywhere in the
tree** (confirmed by grep across all of `src/`) — dead code. Its body contains, verbatim:
```python
floor = {"Witnessed": 0.10, "Instrumented": 0.08, "Transcribed": 0.20,
         "Reconstructed": 0.40, "Disputed": 0.55}.get(attestation, 0.30)
```
Identical key-for-key, value-for-value to `_ATT_BASE`. The live table the comment claims this was
derived from, `assay.SIGMA_BY_ATTESTATION` (`assay.py:379`), computed numerically:
`{'Instrumented': 2.1178, 'Witnessed': 3.2003, 'Transcribed': 4.1573, 'Reconstructed': 5.4907,
'Disputed': 6.6673}`. Normalising both tables to their own max shows the two are **not**
proportional (`_ATT_BASE`: 0.145/0.182/0.364/0.727/1.0 vs. `SIGMA_BY_ATTESTATION`: 0.318/0.480/
0.623/0.824/1.0 for the same five grades in the same order) — they only happen to share a rank
order, which any two sane "how trustworthy is this grade" tables would. `ATTESTATION_QUALITY`
(the thing every Custos's `evidential_part` is actually computed from, `custodes.py:254-259`) is
therefore built on a stale, hand-copied constant from unreachable code, not on the charter's live
attestation model. **Fix**: either derive `_ATT_BASE` from `assay.SIGMA_BY_ATTESTATION` directly
(as the comment claims already happens), or drop the "DERIVED" claim and own it as a second,
independently-chosen table — and separately, delete or wire up the dead `interval_from_hands`.

### 2.2 HIGH — the "one Custos per degree of freedom" 1:1 claim is not real for `currency`: Lumen contributes nothing distinctive to the staleness effect his DOF supposedly owns — REPRODUCED

`custodes.py:195-208` gives Lumen `tilt=0.0, evidence_sensitivity=0.0`. In `_custos_reading()`
(`custodes.py:255-259`), `prior_part = c["tilt"]` and `evidential_part = tilt * evidence_sensitivity
* (1-q)` are therefore **always exactly 0.0** for Lumen — verified numerically. The actual
"currency" effect, `staleness_widening()` (`custodes.py:271-287`), is a free function of
`(distance, years_since)` via `propagation.observed_mark()`, added directly to `half` in
`convene()` (`custodes.py:322-323`) with **no reference to `CUSTODES["Lumen"]` or to `readings` at
all**. Reproduced by monkey-patching `CUSTODES` to remove Lumen entirely and re-running `convene()`
with identical `distance`/`years_since`: `staleness_widening` is bit-identical (`0.5` both times)
whether or not Lumen is in the college. Lumen's only actual effect on the output is his
`axis_emphasis` reweighting of the base `assay()` call — the same kind of contribution any
zero-tilt Custos makes — not anything unique to "currency". `dof_coverage()`'s `one_to_one` check
(`custodes.py:360-366`) only verifies that each Custos's `dof` LABEL set-covers
`DEGREES_OF_FREEDOM`; it does not and cannot detect that one mapping is causally inert. This is
consumed uncritically downstream: `verify_math.py:447-448` asserts `_cov["one_to_one"] == True`
with the note *"the count is derived from the computation, not chosen for aesthetics"* — which is
false for the `currency`/Lumen pairing specifically. **Fix**: either give Lumen a real per-reading
staleness contribution so the DOF mapping is causally 1:1, or document explicitly that "currency"
is handled outside the Custos-reading mechanism and that Lumen is a placeholder standpoint.

### 2.3 MED — `covers_every_reading` is a tautology by construction (self-documented in-line, but consumed as a genuine check by `verify_math.py`) — REPRODUCED

`custodes.py:335-344`:
```python
half = max(1.96 * total_sd, max(abs(v - consensus) for v in vals))
half += stale
...
"covers_every_reading": all(abs(v - consensus) <= half + 1e-12 for v in vals),
```
The module's own comment (lines 335-343) already says this "is a GUARANTEE being published, not a
check being run" and "cannot fail" given how `half` is defined a few lines above. Confirmed by
construction: `half >= max|v - consensus|` always holds since it is one of the two terms taken by
`max()`, and `stale >= 0`. `verify_math.py:454-457` nonetheless asserts it with the framing *"a
college publishing a band that excludes one of its own has hidden its disagreement, not measured
it"* — presenting a tautology as a live regression check without disclosing that it is one.
**Fix**: either add a genuine check of the pre-widening `1.96*sd` band's coverage (which *can*
fail, and is named in the comment as "an addition to the contract" not yet made), or annotate the
`verify_math.py` assertion as a construction-invariant rather than a finding.

### 2.4 Clean

`_custos_reading`, `convene`'s consensus/prior-share math, and Threnody's veto threshold wiring
(`CURL_VETO_THRESHOLD` sourced from `rigor.theorem_1_check`'s CR<0.10 analogy — see finding 3.1 for
a caveat on that analogy itself) are internally consistent and match their docstrings.

---

## 3. `src/rigor.py` — the commensuration engine

### 3.1 HIGH — Theorem 1's editorial claim that Saaty's CR and the Hodge curl fraction "vanish together and grow together" is FALSE in general, though the narrower formal equivalence (both exactly zero) does hold — REPRODUCED

`rigor.py:209-232` docstring: *"What is true, and is all that is needed, is that they vanish
together and increase together: both are measures of the same underlying defect."* This claim is
the stated justification `custodes.py:348-352` gives for using `curl_fraction`'s complement (`eta`)
as Threnody's veto threshold at the "same" bar as Saaty's CR<0.10.

Verified the strict Theorem 1 equivalence holds exactly: an exactly-consistent matrix built via
`consistent_matrix()` gives `CR=0.0, curl_fraction=0.0` exactly, matching (i)-(v) as stated.

But away from exact consistency, reproduced a genuine positive reciprocal 4×4 matrix (small random
log-perturbations around the all-ones matrix) where `CR = 0.0007` (Saaty: "coherent", far under the
0.10 bar) while `curl_fraction = 0.9101` (Hodge: 91% curl — "no scalar is faithful," `custodes.py`'s
own language for Threnody's refusal condition). A 300-trial Monte Carlo sweep over random positive
reciprocal 4×4 matrices at varying noise scales found **40/300 (13%) produced a sharp disagreement**
— one measure calling the matrix coherent (<0.10) while the other called it badly incoherent
(>0.5). The mechanism: `curl_fraction` is a *ratio* of variance components (`grad_sq/(grad_sq +
residual_sq)`), which is numerically unstable exactly when the true signal (`grad_sq`) is small —
i.e. in the low-disagreement, near-uniform-weight regime that is otherwise CR's best case. **This
directly undercuts the load-bearing claim** that licenses reusing the same 0.10 threshold for both
functionals, and by extension undercuts `custodes.py:348-352`'s use of `eta>0.90`/`curl<0.10` as
"the analogous bar" to Saaty's CR<0.10 for Threnody's veto. **Fix**: either restrict the "vanish/
grow together" claim to a bounded neighbourhood of consistency and state the bound, or stop citing
it as license for reusing Saaty's numeric threshold on `curl_fraction`.

### 3.2 MED — `theorem_1_check()`, `consistent_matrix()`, and `mathematical_resonance()` have zero callers anywhere except `rigor.main()`'s own demo printout; the Theorem 1 claim itself is never regression-tested — REPRODUCED (by grep)

Tree-wide grep confirms `theorem_1_check`, `consistent_matrix`, `mathematical_resonance` appear
nowhere outside `rigor.py:763-777,855` (the module's own `__main__` demo). Contrast with every
other public function in this file (`measure_bit_value`, `perron_weights`, `logrank_weights`,
`bradley_terry`, `mdl_bits`, `adjudication_beta`, `lognormal_product`, `prob_at_least_one`,
`ceiling_confidence`, `gumbel_return_level`, `faculty_parity_weights`), all of which are genuinely
exercised with real numeric assertions in `verify_math.py:300-432`. `main()` computes
`t['both_say_consistent']` (a boolean, `rigor.py:772`) and only ever prints it — it is never
asserted anywhere, matching the "self-test computing ok/bad then never asserting" pattern. Given
finding 3.1, the one claim this file calls "load-bearing" for the whole coherence framework is the
one claim with no automated protection against regression. **Fix**: add `theorem_1_check` and
`mathematical_resonance` assertions to `verify_math.py`, at minimum pinning the exact-consistency
equivalence and a documented bound (or absence of one) on the away-from-consistency claim.

### 3.3 Clean — Hard Rule 0 handled correctly and self-documented

`mathematical_resonance()` (`rigor.py:704-717`) explicitly calls out its own compliance: `"load_bearing": sorted(fanout.items(), key=lambda kv: -kv[1])` is commented *"Ranked, never
truncated (Hard Rule 0). The sole consumer slices for display."* — verified the function returns
the full ranked list and only `main()`'s print statement slices `[:6]` for console display
(`rigor.py:860`), never the returned data. `bradley_terry`'s refusal message
(`rigor.py:436-439`) does embed a `[c[:3] for c in comps][:4]` preview inside a human-readable
string, but the actual persisted `components` field (`rigor.py:412`, and `chain.write_result`'s
`"components": [sorted(c) for c in ...]`) is the full, untruncated list — the preview is
message-only and does not corrupt the record. `bradley_terry`, `perron_weights`,
`logrank_weights`, `mdl_bits`, `adjudication_beta`, `lognormal_product`,`prob_at_least_one`,
`ceiling_confidence`, `gumbel_return_level` all read correctly against their cited formulas
(Hunter 2004 MM algorithm, Saaty AHP, Marburger self-focusing constant, Landauer's principle,
Jensen's-inequality Monte Carlo integration) — no numerical bugs found. Ford's-condition handling
(`undefeated`/`winless` computed from `observed`, not the prior-augmented `W`) is correct and
matches its own bug-fix comment.

---

## 4. `src/chain.py` — the Chain of Defeats

### 4.1 MED — Hard Rule 0: `unmatched.most_common(40)` truncates a ranked roster in the PERSISTED artifact, not just a console display — REPRODUCED (by code reading)

`chain.py:108`, inside `write_result()` (the one writer for `data/CHAIN.json`):
```python
"unmatched": (unmatched.most_common(40) if hasattr(unmatched, "most_common")
              else (unmatched or [])),
```
`unmatched` is a `collections.Counter` of every name mentioned in a contest sentence that matched
nothing in the library's catalogue (`chain.py:305,352-354`). `.most_common(40)` ranks it by count
and keeps only the top 40 — exactly "ranking-then-truncating," which Hard Rule 0 prohibits for any
persisted roster. Every unmatched name beyond the 40th most frequent is silently dropped from
`data/CHAIN.json`, which is the one artifact both `chain.main()` and `pipeline.phase_chain` write
this data through. Nothing downstream currently re-reads `CHAIN.json["unmatched"]` (grep confirms
no other module consumes it), so the operational impact today is limited to owner-facing review,
but the persisted record itself is incomplete by construction. **Fix**: persist the full
`Counter` (e.g. `dict(unmatched)` or `unmatched.most_common(None)`), and cap only the console
`print` at `main()`'s existing `.most_common(8)` (`chain.py:457`, display-only, not a Rule 0
violation since nothing is discarded from any stored record).

### 4.2 Clean

`harvest()`'s dedup key (`chain.py:218`, `(entity, full sentence)`) is the already-applied m37 fix
and correctly avoids the prefix-truncation bug it documents. `extract()`'s outcome-to-sentence
binding via the model-reported `index` (not chunk position) is the documented, correctly-applied
fix for the "wrong continuity" bug it describes. `adjudicate_mutuals()`'s epoch-splitting logic is
sound: mutual pairs are only re-keyed when the two sentences date differently; equal or
undated epochs are left standing rather than invented. `write_result`'s and `harvest()`'s use of
`silence.write_json` with per-writer unique temp names (via `silence`, not a hand-rolled fixed
`.tmp` path) correctly closes the two-concurrent-callers collision the comments describe. `fit()`'s
`len(wins) < 3` floor and the `_BAD_CHARS` self-check at import are reasonable, non-tautological
guards.

---

## 5. `src/address.py` — spine codes and the Ladder shelfmark

### 5.1 Confirmed: cannot fabricate a Shelfmark or invent a spine code; unassigned sources are reported, not dropped

`placeholder_shelfmark()` (`address.py:195-201`) always emits the literal `?` rungs and an
`[UNCHARTED -- Ladder-of-Being pass not yet done]` suffix — there is no code path in this file
that fills in a real Shelfmark rung; the function takes only `source_name` and does no lookup at
all. `spine_code_for()` (`address.py:51-116`) falls through four increasingly loose matching
strategies (exact dict key → normalised-letter equality → word-boundary containment → token-overlap
≥0.8) but returns the literal string `"UNASSIGNED"` (line 116) if none matches — it never
synthesises a spine code. Traced `"UNASSIGNED"` downstream: `manifest_builder.py:382,412,452`
buckets any record whose code is `"UNASSIGNED"` and writes it to
`output/index/unassigned_sources.md` rather than silently dropping it, matching this module's own
docstring contract. **Clean** against the special-focus question asked.

### 5.2 LOW — `tier_rank()` silently maps an unrecognised tier string to rank 0 (same as `"volume"`) instead of flagging corruption

`address.py:261-264`:
```python
def tier_rank(tier):
    order = [n for n, _ in TIER_FLOORS]
    return order.index(tier) if tier in order else 0
```
If a corrupted or stale `current` tier value ever reached `promote()` (`address.py:267-281`) that
isn't one of `"volume"/"series"/"grand"/"set"`, this treats it as equivalent to the lowest tier
rather than raising or logging — `promote`'s "demotion never happens" safety property would then
silently mask the corruption rather than surface it, since any earned tier ≥ volume would "win"
without complaint. No live corruption path was found feeding `promote()` in this batch's scope
(`pipeline.py:1708`, out of batch, appears to source `was` from a persisted tier field), so this is
speculative hardening, not a demonstrated live bug. **Fix**: treat an unrecognised `current` as an
error condition worth a `silence.note()`, not a silent rank-0 fallback.

### 5.3 Clean otherwise

The word-boundary containment fix (`address.py:64-84`) and the letter-level-equality-then-word-
boundary-then-token-overlap fallback ladder are well-reasoned and match their extensive inline
justification (DC-Comics / Sword-Coast false-positive history). `recipe_hash()` correctly requires
a content hash, not just an address, per its own docstring's stated rationale. `slugify()`'s `[:60]`
cap truncates a single filename stem, not a roster — not a Rule 0 concern.

---

## 6. `src/render.py` — the nine-tier map/diagram dispatcher

### 6.1 Clean

`TIER_ORDER`/`DRAWN`/`FETCHED` split and `children_of()`'s ancestor-coordinate filtering are
internally consistent; the comment explaining why the gate reads the tree rather than a hardcoded
`SF.TIERS` schema (`render.py:169-175`) is accurate — confirmed `sevenfold` is in fact not imported
anywhere in this file (only named in a comment explaining its removal), so the "kept the import
would fail lint" framing is consistent with the current source. `children_of()`'s return list is
built via `sorted(buckets.items())` with no truncation — no Rule 0 concern. `nm = str(ch.get
("name",""))[:26]` (`render.py:140`) truncates one child's display label inside an SVG for layout
space, not a roster — not a Rule 0 violation. No swallowed failures: `_tree()` raises loudly if
`SEVENFOLD.json` is missing, which is appropriate for a module that cannot function without it.

---

## 7. `src/chord_field.py` — the ki/shrinking unification adjudication

### 7.1 MED — the entire module is dead code: zero callers of any of its six functions or its `ADJUDICATIONS` table anywhere in the tree — REPRODUCED (by grep)

Grepped every public name (`total_beta`, `per_system_beta_without_unification`, `landauer_floor`,
`recoil_momentum`, `recoil_velocity`, `critical_power_self_focus`, `ADJUDICATIONS`) across all of
`src/`, plus `data/`, `state/`, and `config.yaml`: the only hit outside `chord_field.py` itself is
the bare module-name string `"chord_field"` inside `derivation.py:477`'s `SCAN_MODULES` list, which
is a constant-scanning documentation utility (`derivation.scan_constants`) that reads the module's
*source text* for uppercase assignments — it does not import or call anything in `chord_field.py`.
No pipeline phase, no `verify_math.py` check, and no other module actually calls this file's
physics helpers (Landauer floor, recoil momentum, Kerr self-focusing threshold) or reads its
`ADJUDICATIONS` table. The formulas themselves are correct (Marburger self-focusing constant 3.77,
Landauer `kT ln2`, `p=E/c` recoil) and the module is well-documented, but it is currently reference
prose with runnable code attached rather than a wired instrument. **Fix**: either wire
`chord_field`'s `ADJUDICATIONS`/`total_beta()` into wherever the charter's declared `beta_bits`
costs are supposed to be audited (the way `rigor.adjudication_beta` is exercised in
`verify_math.py`), or move it under a docs/reference path if it's meant to stay prose-only.

---

## No secrets found

Grepped all seven files for API-key-shaped strings, bearer tokens, and credential patterns —
`address.py`'s and `cachekey.py`'s only hash usage is `hashlib.sha1`/`sha256` over entity names and
content for cache-key disambiguation and cosmetic base36 coordinates, not secrets. Nothing to
report at the top of this file.
