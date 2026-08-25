# AUDIT — BATCH 16 (run29)

Modules: `build_terminal.py`, `local_agent.py`, `identity.py`, `pantheon.py`, `tempus.py`,
`style_audit.py`, `scale_theories.py`

Every line of each module was read. Findings are reproduced where stated; otherwise marked
VERIFIED-BY-READING or HYPOTHESIS.

---

## local_agent.py — the autonomous Ollama writer

This module got the most scrutiny per the batch's special charge. Its own comments document a
long history of closed holes (m113/m114/m121, case-folding, ADS, prefix-boundary, run #23-#25).
Two holes were pre-identified and were NOT re-derived: `:406-407`'s `modname=None` skipping
gates for non-`.py` files, and `propose_patch` writing `data/records/*.json` directly. What
follows is additional.

### 1. HARD RULE 0 / gate hole — DENYLIST omits the two-writer contract's own enforcement code
**Severity: CRITICAL. REPRODUCED.**

`DENYLIST` at `local_agent.py:52-53` is:
```python
DENYLIST = {"foreman", "silence", "health", "allsweep", "estate", "standards",
            "verify_math", "local_agent"}
```
This is meant to be "the checking machinery may not edit itself" (the error text at
`local_agent.py:432`). But `src/pipeline.py` — the file that literally implements
`write_record()` and `write_record_catalogue()`, the two functions the whole project's
two-writer contract is built on (see its own docstring at `pipeline.py:503-514`, and the
1,051→30,207-entry data-loss incident it exists to prevent) — is **not on the list**. Neither
is `src/runguard.py` (the run-overlap/heartbeat guard whose own header describes bug m27: a
dead run's heartbeat kept being refreshed by someone else's improvised code), nor
`src/gpu_lane.py` (serializes GPU access so this same local_agent rung doesn't starve the
prose-generation lane), nor `src/sweep_plan.py` (the coverage bookkeeping this very audit
records itself into).

Reproduced directly against the running module:
```
$ python -c "import local_agent as la; ...
src/pipeline.py -> modname pipeline denied? False
src/runguard.py -> modname runguard denied? False
src/gpu_lane.py -> modname gpu_lane denied? False
src/sweep_plan.py -> modname sweep_plan denied? False
```
And an actual `t_propose_patch('src/pipeline.py', 'def write_record(path, rec):', ..., apply=False)`
returns `{'applied': False, 'staged': True, 'note': 'run started with --no-apply; patch
recorded for the audit trail'}` — i.e. it clears the denylist gate cleanly — while the same
call against `src/foreman.py` correctly returns `{'applied': False, 'error': 'foreman is on
the denylist...'}`.

Consequence: the local model can propose a patch to `pipeline.write_record`'s merge-on-drift
logic (or to `runguard.claim/beat`'s self-ownership check, or `gpu_lane`'s serialization) and,
provided the patch still parses/lints/imports and `verify_math.py` still prints "0 FAILED"
afterward, it will be **applied**. `verify_math.py` does carry some behavioural tests against
`pipeline.write_record` (confirmed at `verify_math.py:1163-1210`, `3748-3909`) and against
`runguard` (`verify_math.py:1671`), which is real defense-in-depth — but a subtle edit to an
untested branch of either file, or to any OTHER function in those files, would sail through
every remaining gate. The denylist's whole point is to not depend on verify_math catching
everything; for these four files it currently does.

Recommendation for the owner: add `"pipeline"`, `"runguard"`, `"gpu_lane"`, `"sweep_plan"` to
`DENYLIST` (case-folding already covers the rest of the mechanism correctly).

### 2. Correctness bug — double truncation of tool results corrupts JSON silently
**Severity: MEDIUM-HIGH. REPRODUCED.**

`run()` at `local_agent.py:561` feeds every tool result back to the model as:
```python
messages.append({"role": "tool", "content": json.dumps(res)[:SLICE]})
```
`SLICE = 12000` is documented at `local_agent.py:49-51` as "a WINDOW, not a cap... so nothing
silently falls off the end" — but that promise is only honoured by `t_read_file`'s own internal
slicing (which reports `chars_after_slice`). This second truncation, applied to the
**JSON-encoded** string, has no such accounting and no truncation flag.

For any tool result whose raw content needs heavy JSON escaping (backslashes, quotes — not rare
in this codebase's own docstrings, which are full of Windows paths like
`C:\Users\imarl\...`), the serialized JSON can be significantly longer than the 12000-char raw
slice, and the trailing cut lands mid-string, producing **invalid JSON** with no notice to the
model or the operator. Reproduced directly:
```python
text = ('\\"' * 6000)          # 12000 raw chars, backslash-heavy but plausible
res = {'path':'x','offset':0,'slice':text, ...}
s = json.dumps(res)             # length 24085, not 12000
truncated = s[:12000]
json.loads(truncated)           # -> json.decoder.JSONDecodeError:
                                 #    Unterminated string starting at: line 1 column 37
```
Consequence: the model can receive a broken tool response for `read_file` (or `grep`,
`find_symbol`, `run_check`) with no signal that truncation occurred, unlike `t_run_check`'s own
explicit `"truncated"` field. This directly contradicts the module's own "nothing silently
falls off the end" claim (lens category 7 — comment contradicts code) and is a real, if
edge-case-triggered, correctness bug (lens category 1).

### 3. Concurrency note tying #1 to the two-writer contract
**VERIFIED-BY-READING**, cross-referencing the already-known issue (not re-derived): because
`propose_patch` can write `data/records/*.json` directly (bypassing `write_record`'s
merge-on-drift), and because `pipeline.py` itself is not denylisted (finding #1), the same class
of race `write_record` exists to prevent (a stale in-memory copy overwriting a concurrently
re-catalogued file) is reachable through this rung by two independent routes rather than one.

### Everything else in local_agent.py
`_safe()` was tested against absolute-path escapes, drive-letter tricks, and NTFS ADS-style
components and held up — the final `full == HERE or full.startswith(HERE + os.sep)` boundary
check catches every path-join trick tried, because `os.path.join` discarding the base on an
absolute second argument still fails that check. The find-string-must-occur-exactly-once gate,
the case-folded denylist, the revert-on-crash-must-not-claim-success logic, and `_gates()`'s
per-filetype parse/lint/import/verify_math sequence all read correctly and match their comments.

---

## style_audit.py — corpus-wide repetition checker

### Correctness bug — `record_of()` never matches real generated output; silently audits the whole entry instead of the narrative prose
**Severity: HIGH. REPRODUCED.**

`record_of()` at `style_audit.py:48-51`:
```python
def record_of(entry):
    m = re.search(r"The Record\.?\s*(.+?)(?=\n\s*(?:Contradictions|Marginalia|▣|⌁)|\Z)",
                  entry, re.S)
    return (m.group(1) if m else entry).strip()
```
This is supposed to isolate just the "The Record." prose paragraph — the part Ground Rule 6 and
the banned-construction list actually govern — from the Shelfmark/Class/Magnitude/Attestation
header, the Marginalia (which is deliberately supposed to carry distinct per-Hand voices, not
the narrative style rules), the Instrument stat block, and the Threads line.

The entry template in `prompts/system_style.txt:105-127` does instruct the model to print the
literal label "The Record." before the prose. In practice it almost never does:
```
$ grep -rl "The Record\." output/raw/*.md | wc -l
3
$ ls output/raw/*.md | wc -l
144
```
Only 3 of 144 generated chapter files contain that literal string anywhere. Reproduced directly
against a real generated entry (`output/raw/II_C_2_1_Persons_11_13.md`):
```
entries found: 3
record_of() returned 1025 chars out of entry 1029 chars
first 200 chars of "the record": '**Yosh Inouye** (Real Person — Photographer)  \n
Shelfmark: Ω › ? › ? › ? › ? › ? › ? › 2112 (Rush) [UNCHARTED...]  \nClass: Person  \n
Magnitude: unassayed  \nAttestation:'
```
Because the regex fails to match, the fallback `entry` (the whole thing, minus 4 chars) is used
as "the record" for essentially every entry in the real corpus. Every metric this module
reports is downstream of `record_of()`:
- `opener()`/`opener_shape()` measure the first words of "Shelfmark: Ω › ..." or "Class:
  Person", not the actual prose opening — the OPENERS/shapes report is measuring template
  boilerplate for ~98% of the corpus, not narrative style.
- `TELLS.scan(r)` (banned-construction density) scans Marginalia commentary too, polluting
  counts with text that has its own, deliberately different, voice rules.
- em-dash density and `turn_endings` are measured over the whole entry including Marginalia
  and Contradictions, not the Record paragraph the rules target.
- the vocabulary counter scans the same over-broad text.

The tool does not error and prints numbers that look like a completed style audit — exactly the
project's own named failure shape (a result wearing the form of the real one). The self-test
(`--self-test`, `style_audit.py:184-193`) does not catch this because its synthetic corpus
literally contains the string `"The Record."` (line 185-188), so the happy path the self-test
exercises is not the path real data takes — this is a lens-4 "check that cannot fail" in
disguise: it validates the regex against a format the generator doesn't actually produce.

Recommendation: either fix `generate.py`'s prompt-following so "The Record." is reliably
emitted (out of this batch's scope), or make `record_of()` degrade loudly — count and report
how many entries had no match, rather than silently substituting the whole entry — so an
operator reading the audit output would know the numbers are compromised.

### Everything else in style_audit.py
`most_common(top)` calls in `report()` (lines 143, 148, 157, 172) are DISPLAY truncation of a
"top offenders" list for a printed report — the underlying `Counter` objects are built from the
full corpus with no cap, so this is not a Hard Rule 0 violation. The `[◈◈]` character class at
`entries():44` is a harmless redundancy (same Unicode character listed twice), not a bug — the
project's actual entry marker is consistently the single "◈" character per
`prompts/system_style.txt` and `generate.py`.

---

## pantheon.py — hand-authored divine-tier dataset

No findings. This is a small, fixed, hand-curated `GODS` dict (6 entries) scored through
`assay.assay()`; it is not sampling or truncating a larger source (the roster IS the complete
authored set), and the display truncations in `main()` (`epoch[:40]`, `cited[:58]`, `top[:6]`
with an explicit "+N more") are all clearly-labeled print formatting, not data loss. `compute()`
and `value()` read correctly against `assay.py`'s `LADDER`/`BAND_EDGES`. The `Z_FIGHTERS.json`
merge in `main()` uses `dict.setdefault`, so Pantheon entries correctly take precedence without
silently dropping either source; a missing `Z_FIGHTERS.json` is caught by a broad
`except Exception: silence.note(...)`, which is within the project's own established idiom for
non-fatal merges.

---

## tempus.py — omniversal time / simultaneity theory

No findings. Investigated closely because `band_resolution()`'s docstring ("what one decimal
point on ANY axis is worth... /10 per decimal point") looked at first read like it might
mismeasure non-`ruin` axes (whose `BAND_EDGES` ratios per band differ enormously from ruin's —
e.g. M2→M3 spans ~40 bits on `ruin`/`continuity` but only ~6.6 bits on `reach` and ~2.3 bits on
`celerity`) or like the code was missing the `/10` the docstring promises. Both concerns
resolved on closer reading: `band_resolution()` deliberately borrows only the `ruin` axis's band
width as a shared bit-scale for every faculty/physical axis alike — this is the explicit,
argued-for "parity convention" in `rigor.py:100-127` (Ruin 7.0 at M5 and Acumen 7.0 at M5 are
by design equal in bits), not an oversight; the `BAND_EDGES[axis]` values for `reach`/
`celerity`/`sustain`/`continuity` are used elsewhere (`assay.py:219-229`, `measure()`) for a
different purpose — converting a raw physical quantity into its own 0-10 score — not for bit
pricing. And the missing `/10`: `verify_math.py:402-403` and `:3447-3448` explicitly test that
callers (`rigor.measure_bit_value`) divide `band_resolution()`'s return by 10 themselves, so the
function is correct as written and its callers already do the division. `is_present_at()`,
`contemporaneous()`, `rung_description_length()`, `prescience_horizon_bits()`, and
`retrocausality_beta()` all read correctly against their own docstrings.

---

## scale_theories.py — size-change physics theories

No findings of consequence. `bulk_export_beta()`, `growth_strike()`, and
`penetration_pressure()` are simplified in-fiction physics (impulse-over-time as a force
proxy, etc.) consistent with their own stated approximations, not software bugs. One low-severity
observation: `surviving_theory()` (`scale_theories.py:145-148`) selects the surviving candidate
by testing `t["falsified_by"].startswith("Nothing attested")` — a string-prefix match against
hand-authored prose rather than a boolean field. It works today because exactly one of the four
`THEORIES` entries carries that exact phrasing, but it is a fragile pattern (lens category 4
territory: a check keyed on an incidental string match rather than a structural flag) — if a
future edit to `T3_BULK_EXPORT`'s `falsified_by` text changed the wording even slightly, or a
fifth theory were added with different phrasing for "not falsified," this would silently return
the wrong set (or none) with no error. Not scored as a full finding since nothing currently
depends on this beyond this module's own theoretical framing, but worth a boolean
`survives: True/False` field if this module is extended.

---

## build_terminal.py — Registry Terminal HTML/JS generator

No new findings. This module's own comments document a substantial prior hardening pass (BUGS
m10: unescaped catalogue names breaking out of `<script>` and `innerHTML`, both fixed with
`esc()` on the JS side and a `<` → `\u003c` neutralization on the Python side before splicing
into the template; the Hard-Rule-0 fix that removed an 8-item roster cap in favor of a
scrollable `.roster` div at CSS line 52-55; the `holds` SUM-not-short-circuit fix at
`panel():480-484`). Checked and confirmed correct on this pass:
- `main()`'s `data.replace("<", "\\u003c")` operates on the raw JSON text before splicing, and
  because `<` is a valid, semantically-neutral JSON string escape, this changes no data the
  browser will render — verified by reasoning through the JSON string-escape rules; every `<` in
  a source name still round-trips to `<` after `JSON.parse`.
- No JS-side array (`ss`, `ws`, `kids`, `DATA.roots`) is ever `.slice()`'d or otherwise capped —
  only individual label *strings* are truncated for on-canvas display (`nm.slice(0,22)`, etc.),
  always with the full name still available via the SVG `<title>` tooltip and the side panel.
  This is DISPLAY truncation, not data truncation, consistent with Hard Rule 0.
- `dotR()`'s gap computation, `layout()`'s wedge-weighting recursion, and the pan/zoom/clamp
  logic in `applyView()`/`clampView()`/`bindStage()` all read correctly against their own
  in-code rationale comments; no divide-by-zero or off-by-one found on inspection.

---

## Coverage

All seven modules read in full; findings above cover local_agent.py (3 items, 1 critical) and
style_audit.py (1 high-severity item). identity.py, pantheon.py, tempus.py, scale_theories.py,
and build_terminal.py produced no findings beyond one low-severity observation in
scale_theories.py.
