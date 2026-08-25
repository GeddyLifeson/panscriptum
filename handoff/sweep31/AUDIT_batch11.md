# AUDIT — sweep run31, BATCH 11

Modules: `src/drill.py` (892 lines), `src/generate.py` (497), `src/custodes.py` (418),
`src/ingest_doc.py` (302), `src/hosts.py` (253), `src/tells.py` (215), `src/repass_bands.py` (119),
`src/lognames.py` (36).

Total lines read: 2,532 (every line of all eight files, plus targeted reads of `src/prose_gate.py`,
`src/assay.py`, `src/pipeline.py`, `src/overnight.py`, `src/anchors.py` to verify claims made
against them). Read-only throughout; no file written except this report. `drill.py` was read, never
executed, per instructions.

---

## FINDING 1 — drill.py: a "COVERAGE.json unreadable" net that cannot test what it claims

**File:line:** `src/drill.py:110-115` (net inside `drill_queue`)

```python
net(a, "COVERAGE.json unreadable is a refusal, not a pass",
    lambda: PG.cited_fraction("anything", None) is None
    or PG.evidence_ok("nope", 0.35, [])[0] is False,
    "unknown must mean stop")
```

**Why it is wrong.** `prose_gate.cited_fraction(source, rows=None)` only touches disk when `rows`
is `None`; it then calls `_coverage_rows()` inside a try/except and returns `None` on failure — but
it *also* returns `None` from its normal "no matching row" branch (`prose_gate.py:160`,
`return None` after the `for r in rows` loop finds nothing). The source name passed here,
`"anything"`, is not a real entry in the live `data/COVERAGE.json`, so this call returns `None`
via the **ordinary not-found path**, never touching the unreadable-file except-clause at all. The
second disjunct passes `rows=[]` explicitly, which also bypasses any file read. **Neither clause
of this attack ever makes `COVERAGE.json` unreadable.** Because the two clauses are joined with
`or`, and because the label's actual claim (file unreadable) is never exercised by either, this
net would report **HELD** even if the except-clause at `prose_gate.py:152-153` (the only code that
answers "what happens when the file cannot be read") were deleted entirely — the "source not
found" branch alone keeps both disjuncts true forever. This is precisely a **drill net that
cannot fail**: it is not attacking the guard it names.

**Concrete scenario:** Delete the `try/except` around `_coverage_rows()` in `cited_fraction` (or
otherwise break unreadable-file handling) → this net still prints `HELD` because "anything" was
never a real source and `evidence_ok("nope", 0.35, [])` is a duplicate of the *separate*,
correctly-targeted "an unmeasured source is refused" net a few lines above it (`drill.py:107-109`).

**Severity:** blocking (this is exactly the failure class the task brief asks to prioritize — a
net that cannot report BREACHED for the guard it names).
**Confidence:** VERIFIED (read `prose_gate.py:143-183`, traced both code paths).

---

## FINDING 2 — drill.py: `_gates_agree()` writes directly to the live `config.yaml`, non-atomically, contradicting the module's own safety claim

**File:line:** `src/drill.py:267-284`, called from the net at `src/drill.py:250`

```python
def _gates_agree():
    ...
    real = os.path.join(HERE, "config.yaml")
    saved = open(real, encoding="utf-8").read()
    try:
        for val in ('"false"', '"true"', '1', '"no"', 'yes'):
            cfg = yaml.safe_load(saved) or {}
            cfg["prose_enabled"] = yaml.safe_load(val)
            with open(real, "w", encoding="utf-8") as f:      # <-- plain open(),  not atomic
                yaml.safe_dump(cfg, f)
            if ON._prose_enabled() != PG.gate_open()[0]:
                return False
        return True
    finally:
        with open(real, "w", encoding="utf-8") as f:          # <-- plain open() again
            f.write(saved)
```

**Why it is wrong.** The module docstring (`drill.py:13-14`) promises: *"It never writes to the
corpus... Every attack is constructed in memory or in a scratch directory. `--to-halt` is the one
exception..."* This function writes the **real, live `config.yaml`** — the exact file that gates
prose generation for the whole system — up to five times per run, using a bare `open(path, "w")` +
`yaml.safe_dump`, which is precisely the **truncate-then-fill** pattern that `silence.write_json`'s
own docstring (`silence.py:290-309`) says this project spent a comprehensive sweep eliminating
("a crash in the gap leaves it that way permanently"). If the process is killed (task manager,
OOM, power loss, Ctrl-Break) between the `open(real,"w")` and the `yaml.safe_dump` completing —
or, worse, right after a write where `val` was `'yes'` (which YAML parses as boolean `True`) — the
**real `config.yaml` is left with `prose_enabled: true`**, silently opening the actual prose gate
for every subsequent run, until an owner happens to notice. The `finally` block's restore write
has the identical hazard on its own crash window. Note this module is exactly the audit that is
supposed to prove interlocks work; here it is the one piece of code in the batch that bypasses the
project's own atomic-write discipline on a file more consequential than most it protects.

**Concrete scenario:** kill `python src/drill.py` (SIGKILL/taskkill /F) at the instant the loop
has just written `cfg["prose_enabled"]=True` (the `'yes'` iteration) and not yet reached the next
loop iteration or the `finally` restore → `config.yaml` on disk now reads `prose_enabled: true`
permanently, and the next `overnight.py` run or `generate.py` invocation treats the prose gate as
genuinely opened by the owner.

**Severity:** blocking (a "read-only, audit-only" tool with a real, non-atomic, crash-unsafe write
path to the single most safety-critical config file in the project; also a direct contradiction of
the module's own docstring — Lens 6).
**Confidence:** VERIFIED (read the function in full; cross-checked `silence.write_json`'s stated
purpose against this write style).

---

## FINDING 3 — drill.py: `guards_are_wired_where_claimed()` is a substring-presence check, not a call-site check

**File:line:** `src/drill.py:853-864`

```python
def guards_are_wired_where_claimed():
    want = {"generate.py": "assert_gate_open", "overnight.py": "_prose_enabled()",
            "coverage.py": "cachekey", "feats.py": "cachekey",
            "pipeline.py": "cachekey", "hostcheck.py": "cachekey"}
    for f, token in want.items():
        with open(os.path.join(src, f), encoding="utf-8") as fh:
            if token not in fh.read():
                return False
    return True
```

**Why it is wrong.** This checks only that a literal token string (e.g. `"cachekey"`) appears
*anywhere* in the named file — in a comment, a docstring, a dead import, an unreachable branch, or
a `# TODO: wire up cachekey` note would all satisfy it identically to a genuine call site. It does
not verify the token is invoked, that the invocation is reachable, or that its result is checked.
This is the same shape of defect as the withdrawal-script net below (Finding 4) and is exactly
"a check that cannot fail": if `generate.py`'s real call to `assert_gate_open(cfg)` (currently at
`generate.py:349`) were deleted but the string `assert_gate_open` remained in a comment explaining
why it *used to* be called, this net would still report HELD.

**Concrete scenario:** replace `import cachekey as CK ... CK.owns(...)` in `coverage.py` with a
comment `# cachekey check removed pending refactor, cachekey` and delete the real call → the net
still prints HELD because the bare word "cachekey" is still present in the file.

**Severity:** major (this is the guard whose entire job is to catch "a guard DELETED, not a guard
that failed" per its own comment at `drill.py:864` — and it is evadable by leaving the token in a
comment).
**Confidence:** VERIFIED (read the function; the check is literally `token not in fh.read()`).

---

## FINDING 4 — drill.py: "the withdrawal script takes one before moving anything" tests for the word "snapshot", not for a snapshot being taken

**File:line:** `src/drill.py:676-680`

```python
net(a, "the withdrawal script takes one before moving anything",
    lambda: "snapshot" in open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "withdraw_chapters.py"),
        encoding="utf-8").read(),
    "145 chapters were withdrawn with nothing but an instinct behind them")
```

**Why it is wrong.** Same defect as Finding 3, on the exact guard the incident it cites (145
chapters withdrawn with no backup) was meant to prevent. `"snapshot" in <full file text>` is
satisfied by an unused `import snapshot`, a comment, a variable named `snapshot_dir` that is never
passed to `SNAP.before()`, or a call that exists but runs *after* the destructive move rather than
before it. The net's own name ("takes one **before** moving anything") asserts an ordering
property that a whole-file substring search structurally cannot verify.

**Concrete scenario:** reorder `withdraw_chapters.py` so the file-move happens first and
`SNAP.before(...)` is called afterward (or not at all, leaving only a stale `import snapshot`) →
this net still reports HELD.

**Severity:** major (this is a "check that cannot fail" guarding the exact incident described in
its own expectation string).
**Confidence:** VERIFIED.

---

## FINDING 5 — drill.py: `_no_programmatic_clear()` is defeated by any import alias other than `escalation`/`ESC`

**File:line:** `src/drill.py:546-555`

```python
def _no_programmatic_clear():
    for f in sorted(os.listdir(src)):
        ...
        if "escalation.clear(" in t or "ESC.clear(" in t:
            return False
    return True
```

**Why it is wrong.** The scan only recognizes two exact spellings of the call. A module that does
`import escalation as E; E.clear(...)`, or `from escalation import clear as _c; _c(...)`, or
`getattr(escalation, "clear")(...)` clears the halt programmatically and is invisible to this
check — the module continues to report "no module clears the halt" (HELD) regardless. This is
lens 7's "a regex that never matches what it claims to forbid," scoped to two hardcoded aliases in
a codebase where every other module chooses its own import alias freely (confirmed: `drill.py`
itself imports `escalation as ESC`, and nothing stops any file from picking a third name). Errs on
the *safe* side only for the false-positive case (an alias named literally `ESC` used in an
unrelated comment); it is silent on the dangerous case (a real bypass under a different alias).

**Severity:** minor (no evidence any module currently does this; the check is a narrow net around
a specific literal, not a structural one).
**Confidence:** VERIFIED code reading; HYPOTHESIS that it is exploitable in practice (no such
alias currently exists in `src/`).

---

## FINDING 6 — drill.py: two `drill_inspector` nets vacuously pass when their target file is absent

**File:line:** `src/drill.py:811-819` (`catalog_matches_disk`), `src/drill.py:829-838`
(`coverage_totals_are_recomputable`)

```python
def catalog_matches_disk():
    cat = os.path.join(HERE, "output", "index", "catalog.json")
    if not os.path.exists(cat):
        return True          # <-- vacuous HELD
    ...
```

**Why it is wrong.** Both inspector nets exist specifically to catch "a report that had drifted
from the thing it described" (the function's own module docstring, `drill.py:724-732`). If
`output/index/catalog.json` or `data/COVERAGE.json` were themselves accidentally deleted or moved
— itself exactly the kind of silent, consequential drift this inspector layer is built to catch —
both nets report **HELD**, not "cannot verify" or "target missing." A missing catalog is not
evidence the catalog matches disk; it is evidence there is no catalog to check, which is a
distinct and equally alarming state that this design cannot distinguish from "everything is fine."

**Severity:** minor (both files exist today in the live tree, so this is a latent gap rather than
a live failure; but it is precisely the class of drift the surrounding docstring calls the
project's most expensive failure mode).
**Confidence:** VERIFIED.

---

## FINDING 7 — drill.py: main()'s real halt-on-breach and config.yaml write both contradict the "constructed in memory or scratch directory" / "--to-halt is the one exception" docstring claim

**File:line:** `src/drill.py:13-14` (the claim) vs. `src/drill.py:267-284` (Finding 2) and
`src/drill.py:869-875` (`if breached: ESC.escalate(ESC.OWNER, "DRILL_BREACH", ...)`)

**Why it is wrong.** The docstring states plainly that `--to-halt` is "the one exception" to
"never writes to the corpus... constructed in memory or in a scratch directory." In fact **any**
run of `drill.py` — with or without `--to-halt` — that finds even one BREACHED net raises a real
`ESC.escalate(ESC.OWNER, "DRILL_BREACH", ...)` and halts the library for real (`drill.py:869-878`,
`return 1`), and `_gates_agree()` (Finding 2) writes the live `config.yaml` on every run
regardless of flags. Both are real-state mutations the docstring says do not happen outside
`--to-halt`. (The on-breach halt is very likely *intentional* and defensible on its own — "a
safety that does not refuse is worse than an absent one" is a reasonable design — but the
docstring's wording overclaims what the tool does, which matters for anyone deciding whether it is
safe to run unattended. This is the likely reason the task brief instructs never to run
`drill.py`.)

**Severity:** minor (documentation/contract mismatch, not a new mechanism bug beyond Findings 2 and
the by-design escalate-on-breach), filed separately because it is a Lens-6 docstring contradiction
in its own right.
**Confidence:** VERIFIED.

---

## FINDING 8 — tells.py: `"not merely X but Y"` regex matches "not merely"/"not simply" alone, with no "but" required

**File:line:** `src/tells.py:70`

```python
"not merely X but Y": r"\bnot merely\b|\bnot simply\b|\bnot just\b.{0,40}\bbut\b",
```

**Why it is wrong.** Regex alternation (`|`) has the lowest precedence, so this compiles to three
independent alternatives: `\bnot merely\b`, OR `\bnot simply\b`, OR `\bnot just\b.{0,40}\bbut\b`.
Only the third alternative requires the "but Y" continuation the pattern's own name promises. The
first two match "not merely" / "not simply" **standalone**, with no trailing "but" anywhere in the
sentence.

```
>>> re.findall(r"\bnot merely\b|\bnot simply\b|\bnot just\b.{0,40}\bbut\b",
...            "It is not merely a house.", re.I)
['not merely']
>>> re.findall(..., "It was not just a place.", re.I)
[]
```

**Concrete scenario:** a generated entry containing "not merely a fortress" with no "but"
continuation anywhere nearby gets flagged as the structural tell "not merely X but Y" even though
the reveal-shape sentence this tell exists to catch was never written. Inconsistent with "not
just", which correctly requires the "but" continuation. Inflates false positives in the audit
without changing the prompt's own list (which bans "not merely"/"not simply" nowhere as standalone
lexical items — this STRUCTURAL entry is the only place they are checked, and it checks them in
the wrong shape for two of its three alternatives).

**Severity:** minor (affects the accuracy of a prose audit heuristic, not corpus data or a gate).
**Confidence:** VERIFIED (ran the regex).

---

## FINDING 9 — custodes.py: Threnody's per-reading veto is dead output; the real veto depends entirely on a caller-supplied `eta` that the only production caller never passes

**File:line:** `src/custodes.py:183` (`veto=True` in the CUSTODES table), `src/custodes.py:267`
(`"veto": bool(c.get("veto"))` returned per-reading), `src/custodes.py:290-357` (`convene()`),
cross-checked against `src/anchors.py:190` (the only production caller of `convene()`)

**Why it is wrong.** `custodes.py`'s docstring and the CUSTODES table describe Threnody as
"uniquely a veto: it can deny the output rather than move it" (line 81) and "Hers is the only
standpoint that can refuse the output rather than shift it" (line 178). `_custos_reading()`
computes and returns a `"veto"` field per Custos (line 267) — but `convene()` never reads
`reading["veto"]` anywhere; `vals`, `perfect`, and `out["reading_spread"]` are all built from the
`readings` list without ever consulting that key. The **actual** veto mechanism is a completely
separate code path gated by the `eta` parameter (`convene(..., eta=None, ...)`, default `None`)
and `CURL_VETO_THRESHOLD` (lines 352-356), described as coming "from `resonance.hodge_decompose`"
(line 297) — but nothing inside `convene()` or its production caller computes `eta` from
`resonance.hodge_decompose`. The **only** production call site, `anchors.py:190`
(`col = CU.convene(a["anchor"], a["scores"], attestation=a["attestation"], worksheet="anchors.py")`),
does not pass `eta` at all, so `eta` is always `None` there and the `if eta is not None and ...`
branch (line 352) never executes. Threnody's documented veto capability is therefore **inert in
the one place the college is actually convened** — she contributes an ordinary numeric reading
(tilt 0.0, evidence_sensitivity 0.10) indistinguishable from any other standpoint, and "the only
standpoint that can refuse the output" silently never refuses anything unless some future caller
remembers to wire up `eta` from `resonance.hodge_decompose` itself.

**Concrete scenario:** feed `anchors.py` a being whose contest structure is substantially curl
(non-transitive) — exactly the case Threnody's veto exists for — and `CU.convene(...)` will still
publish a numeric consensus and interval with no veto ever firing, because `anchors.py` never
computes or passes `eta`.

**Severity:** major (a documented safety/correctness mechanism — "refuse the output rather than
shift it" — that is unreachable from the module's only real caller, with no error or warning to
say so).
**Confidence:** VERIFIED (grepped every call site of `custodes.convene` in `src/`; only
`anchors.py`, `verify_math.py` self-tests, and `custodes.py`'s own `main()` demo call it, and only
the self-tests/demo ever pass `eta`).

---

## FINDING 10 — custodes.py: unknown attestation grade defaults to a *moderate* quality (0.4) instead of the worst-case, breaking the project's own stated monotonicity invariant

**File:line:** `src/custodes.py:254`

```python
q = ATTESTATION_QUALITY.get(attestation, 0.4)
```

**Why it is wrong.** `assay.py` establishes, as an explicit invariant with its own comment trail
(`assay.py:358-399`), that "ignorance is never narrower than the worst testimony" — an unknown or
unrecognized attestation grade must map to the worst-case sigma (`SIGMA_BY_ATTESTATION.get(attestation, SIGMA_MAX)`,
`assay.py:552`), never something better. `custodes.py`'s parallel table, `ATTESTATION_QUALITY`,
computes quality 0 for the worst known grade ("Disputed") and ~0.82/~0.85/~0.64/~0.27 for the
other four — but its `.get(attestation, 0.4)` fallback for an *unrecognized* string gives quality
0.4, which sits **between** "Reconstructed" (0.27) and "Transcribed" (0.64), not at the
"Disputed" floor of 0. A malformed, mistyped, or unexpected attestation string (e.g. a future
grade added to the corpus schema but not yet added to this five-entry table) is therefore treated
as *moderately trustworthy* rather than maximally uncertain, silently narrowing that Custos's
interval contribution below what the project's own stated invariant calls for.

**Concrete scenario:** a record entry carries `attestation="Contemporary"` (a plausible future or
typo'd grade not in `_ATT_BASE`) → `ATTESTATION_QUALITY.get("Contemporary", 0.4)` returns 0.4
instead of the worst-case 0, so that Custos's `evidential_part` shrinks less than it should and
the college's published `±` is narrower than the "more ignorance can never buy a narrower bar"
rule this codebase enforces elsewhere.

**Severity:** major (silently inverts a stated safety invariant on malformed input, in the exact
module whose own docstring is about measuring disagreement honestly).
**Confidence:** VERIFIED (compared against `assay.py`'s explicit fallback and its documented
monotonicity invariant).

---

## FINDING 11 — custodes.py: the "guarantee" `covers_every_reading` is a tautology by the code's own design, self-documented but still worth flagging per Lens 7

**File:line:** `src/custodes.py:335-344`

The code's own comment says it plainly: `half` is `max(1.96*sd, max|v-consensus|)` and only ever
widened afterward, so `covers_every_reading = all(abs(v-consensus) <= half + 1e-12 for v in vals)`
"is true by construction for every possible input and cannot fail." This is exactly Lens 7's
"check that cannot fail." It is already flagged in-code as non-verification, which is good
practice, but is included here per the task's "report every one" instruction, and because a
downstream reader of `convene()`'s output dict who does not read this comment could still mistake
the field for a live check (which is the risk the comment itself names).

**Severity:** cosmetic (self-documented, not misleading to anyone who reads the surrounding
comment).
**Confidence:** VERIFIED.

---

## FINDING 12 — ingest_doc.py: `[:2000]` truncation of a mined entity's description is a HARD RULE 0 cap

**File:line:** `src/ingest_doc.py:216`

```python
"description": (e.get("description") or "").strip()[:2000],
```

**Why it is wrong.** The module's own docstring calls this "an uncapped entity-extraction pass"
and states "HARD RULE 0 APPLIES" (`ingest_doc.py:9-12`) — yet the description text written
permanently into the record is hard-truncated at 2000 characters with no comment justifying the
number and no warning logged when truncation actually occurs. This is a real, persisted cap on
data written to the corpus (not a print-only sample), matching HARD RULE 0's literal text
("`[:N]`... that makes the universe smaller than it really is").

**Concrete scenario:** a passage yields a rich, well-evidenced 2,400-character description for a
major entity (a book's central figure, described across a full page) → the stored record silently
keeps only the first 2000 characters, with the remainder discarded and no record that a cut
occurred.

**Severity:** minor-to-major (depends on how often the model actually emits >2000-char
descriptions in practice; the cap exists regardless and is silent).
**Confidence:** VERIFIED (code reading); frequency of actual triggering is HYPOTHESIS.

---

## FINDING 13 — ingest_doc.py: `record_path()`'s containment fallback can bind a new source to an unrelated record, and iterates non-`.json` files unsafely

**File:line:** `src/ingest_doc.py:116-126`

```python
def record_path(source):
    p = os.path.join(RECORDS, slug(source) + ".json")
    if os.path.exists(p):
        return p
    want = slug(source)
    for fn in os.listdir(RECORDS):
        base = fn[:-5]
        if want in base or base in want:
            return os.path.join(RECORDS, fn)
    return p
```

**Why it is wrong.** Two compounding problems. (1) `base in want` matches whenever an *existing*
record's slug is a **substring** of the *new* source's slug — e.g. an existing `alien.json` would
match a brand-new source "Alien vs Predator" (slug `alien-vs-predator`, which contains `alien`),
silently binding newly-mined entities into the wrong, unrelated record. (2) `os.listdir(RECORDS)`
order is not guaranteed, so which of several possible containment matches wins is nondeterministic
across OSes/runs. (3) The loop does not filter to `.json` files before slicing `fn[:-5]` — it
scans *every* file in `data/records/`, including any stray non-`.json` artifact. This is not
hypothetical: `data/records/getter-robo.json.precatfix` (a 77,857-byte leftover backup file,
confirmed present alongside the live `data/records/getter-robo.json`, 73,843 bytes, both dated
2026-08-22) already sits in the live `RECORDS` directory today. Had "getter-robo" not also had an
exact-match file (so the exact-match branch at line 118 short-circuits first), any source whose
slug happens to relate to `"getter-robo.json.prec"` (the corrupted `base` this stray file produces
via `fn[:-5]`) would risk matching this backup file instead of a real record — and `mine()`
(`ingest_doc.py:174-176`) does `json.load()` on whatever `record_path()` returns with no
`.json`-suffix or validity guard.

**Concrete scenario:** ingest a new PDF for a source whose slug is a superset of some *other*,
already-catalogued record's slug and which has no record file of its own yet → the mined entities
get appended not to a fresh record for the new source, but silently merged into the unrelated
existing record, via the exact-containment fallback.

**Severity:** major (silent cross-contamination between two different corpus sources' records is a
serious data-integrity issue, though the trigger requires a specific slug-containment
coincidence).
**Confidence:** VERIFIED for the code defect and the stray non-`.json` file's presence; HYPOTHESIS
for how often the containment collision itself actually fires (checked all 217 live record slugs
for pairwise containment — found only the stray-file artifact above, no genuine two-source
collision today).

---

## FINDING 14 — generate.py: `failures.json` entries are never cleared on a later success

**File:line:** `src/generate.py:443-482` (the whole per-job loop); confirmed via
`grep -n "\.pop(" src/generate.py` returning no matches

**Why it is wrong.** `failures[job["address"]] = {...}` is written on every failure
(`generate.py:449`), but nothing anywhere in the module ever removes a job's entry from
`failures` — including in the success path immediately below (`generate.py:458-482`), which
writes a fresh, correct `catalog[job["address"]]` entry but leaves any prior `failures` entry for
that same address untouched. Once cached under a new `recipe_hash`, that job is also permanently
excluded from `pending` on future runs (`generate.py:401-403`), so it will never be revisited to
clean up its own stale failure record either. `failures.json` is described as a "failure log" the
module "maintains" (module docstring, line 4) — a resource presumably read by a human or a
dashboard deciding what still needs attention.

**Concrete scenario:** a job fails once (transient Ollama timeout), is logged to
`failures.json`, then succeeds on the very next run and is correctly catalogued → its
`failures.json` entry remains forever, so anyone reading `failures.json` sees a job reported as
broken that has, in fact, long since succeeded.

**Severity:** major (stale operational state that misrepresents current corpus health; matches the
project's own stated sensitivity to reports drifting from reality, per `drill.py`'s inspector
layer docstring in the same batch).
**Confidence:** VERIFIED.

---

## FINDING 15 — generate.py: `--limit` truncates `pending` before it is reported, so the printed "N pending" count silently means "N this run," not "N total pending"

**File:line:** `src/generate.py:421-425`

```python
if args.limit:
    pending = pending[: args.limit]

print(f"{len(jobs)} total jobs, {len(pending)} pending (not yet cached under current "
      f"model={model} seed={seed} prompt_version={prompt_version})")
```

**Why it is wrong.** `pending` is truncated to `args.limit` *before* the summary line is printed,
so a user running `--limit 20` against a manifest with, say, 500 genuinely uncached jobs sees
"500 total jobs, 20 pending" — which reads as "only 20 jobs remain to be generated," not "500
remain, this invocation will only process 20 of them." The word "pending" is used elsewhere in the
same function (line 402's comment, "already generated from this exact source data...") to mean
"not yet cached," which is exactly the number this print statement obscures once `--limit` is in
play. Purely a reporting/UX defect — the actual generation loop and cache bookkeeping are
unaffected — but it is the specific pattern HARD RULE 0 names (`--limit` silently shrinking what
is reported as "the universe" of remaining work) even though no corpus data is actually lost.
**Severity:** minor.
**Confidence:** VERIFIED (code order read directly).

---

## FINDING 16 — repass_bands.py: "of 211" is a hardcoded denominator in a live report line, not derived from the actual record count processed

**File:line:** `src/repass_bands.py:98`

```python
print(f"  demoted to unassayed: {len(demoted_sources):,} of 211")
```

**Why it is wrong.** Every other `recs = PL.records()`-derived count in this script (`total_banded`,
`len(kept_entries)`, etc.) is computed live from the corpus actually read this run. This one line
alone hardcodes the historical total (211), rather than deriving it from `len(recs)` or an
equivalent live count. Elsewhere in the codebase "211" appears only inside comments and docstrings
describing a *historical* measurement at a point in time (`feats.py:17`, `pipeline.py:785`,
`scope.py:11`, `weave.py:43/162/280`) — this is the only place it is baked into a live,
re-runnable numeric report. If the corpus has grown or shrunk since the number was measured (e.g.
new sources added via `ingest_doc.py`, which is in this very batch and exists specifically to grow
the corpus), a re-run of `repass_bands.py --apply` would print a source-ceiling fraction against
a stale, wrong denominator.

**Severity:** minor (display-only; does not affect what gets demoted or written).
**Confidence:** VERIFIED (the number is a literal, not computed); staleness itself is HYPOTHESIS
(depends on whether the corpus has actually changed size since the constant was written).

---

## FINDING 17 — lognames.py: `PIPELINE`'s bare `"pipeline.py"` fragment does not meet the module's own stated specificity standard

**File:line:** `src/lognames.py:32`, cross-checked against `src/pipeline.py:39-41` and
`src/overnight.py:170-171`

**Why it is wrong.** The module's own comment (`lognames.py:26-28`) states the OWNER fragment
"must be specific enough to distinguish two invocations of the same script: `feats.py --roll` is
the page roll, a bare `feats.py` is something else" — and the table honors that standard for
`READ` (`"read.py --run"`), `ROLL` (`"feats.py --roll"`), `RECATALOGUE`
(`"catalogue_web.py --recatalogue"`), and `CALIBRATE` (`"magnitude.py --calibrate"`). `PIPELINE`
is left bare (`"pipeline.py"`), even though `pipeline.py` itself documents multiple invocation
modes (`--status`, `--phase N`, or bare "run all implemented phases in order, forever" —
`pipeline.py:39-41`), and `overnight.running(fragment)` matches by plain substring
(`fragment in cmd`, `overnight.py:170-171`) with no anchoring. A bare `"pipeline.py"` therefore
matches an operator's `python src/pipeline.py --status` health check exactly as readily as the
supervisor's own long-running bare invocation.

**Concrete scenario:** the supervisor's `pipeline.py` job (writer of `pipeline_auto.log`) dies
silently; an operator happens to run `python src/pipeline.py --status` moments later to check on
it → `overnight.running("pipeline.py")` returns True (matching the `--status` process), so the
stall detector concludes the writer is "still up" and does not flag `pipeline_auto.log` as stalled
— the exact false-negative failure mode this module's own docstring (lines 17-24) describes as the
motivating incident for the whole file.
**Severity:** minor (requires a coincidental manual `--status` run at the wrong moment; `SWEEP`
has the same bareness but `sweep.py` was not confirmed to have multiple invocation modes).
**Confidence:** VERIFIED that the fragment is bare and that `pipeline.py` has multiple invocation
modes and that matching is substring-based; HYPOTHESIS that this has actually caused a missed
stall in practice.

---

## Summary by severity

- **Blocking:** 2 (Findings 1, 2)
- **Major:** 6 (Findings 3, 4, 9, 10, 13, 14)
- **Minor:** 8 (Findings 5, 6, 7, 8, 12, 15, 16, 17)
- **Cosmetic:** 1 (Finding 11)

All 17 findings are VERIFIED against source unless noted; three (13, 16, 17) carry an explicit
HYPOTHESIS component about real-world trigger frequency, flagged as such inline.
