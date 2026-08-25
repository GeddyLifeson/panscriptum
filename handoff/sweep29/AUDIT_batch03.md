# AUDIT — batch 03, run29

Modules read in full: `src/standards.py` (1471 lines), `src/pick_model.py` (357 lines),
`src/navtree.py` (272 lines), `src/catalogue_codex.py` (215 lines), `src/retry_synthesis.py`
(164 lines).

Method: every module was read line-by-line; every finding below with a REPRODUCED tag was
driven with a throwaway script under the session scratchpad, using
`PYTHONIOENCODING=utf-8 C:/Users/imarl/miniconda3/python.exe`, against this repo's real code
(and in two cases, real data files) unless stated otherwise. No file under `src/` was edited.
One reproduction (the `standards.py` JOB_WATCH race) transiently overwrote
`state/job_progress.json`; it was deleted afterward so the system regenerates it cleanly next
run (safe — `job_stamp()` treats a missing previous entry as "not held", so no false stall
results).

---

## src/retry_synthesis.py

### 1. HIGH — `synthesise()` (line 56-67) silently reintroduces bug m13, the Hard-Rule-0 sampling clamp `pipeline.py` was fixed to remove — REPRODUCED

**Claim (docstring, line 57-58):** "Byte-identical prompt construction to `phase_synthesis`, so a
retried source is not scored by a different method than its neighbours."

**What the code actually does (line 60):**
```python
sample = sorted(rec["entries"], key=lambda e: -len(e.get("description", "")))[:14]
```
A single hard cap of the top 14 entries **by description length only** — no feats considered.

**What `phase_synthesis` (pipeline.py:685-694) actually does:** every mined-feat-bearing entry
is nominated, chunked 14-at-a-time across as many chunks as needed (`with_feats[i:i+14]`, no
truncation of the feat-bearing set), and the best band across all chunks wins. Only when there
are **zero** feat-bearing entries does it fall back to a single `rest[:14]` chunk. Pipeline.py's
own comment names this exactly: *"the fixed sample-of-14 could silently clamp a whole source to
a lesser ceiling whenever the true strongest entity ranked fifteenth by feat-count... (BUGS m13,
Hard-Rule-0-shaped, ruled by the owner 2026-08-24: FIX IT ALL)."*

`retry_synthesis.synthesise()` is exactly the pre-fix shape m13 describes, reintroduced in the
one file whose entire job is retrying sources that already failed once — i.e. the population
most likely to need the correct sampling.

**Reproduced** (`/tmp/repro_synth_sampling.py`, copying both sampling snippets verbatim): built
a synthetic source with 19 long-description, feat-less entries and one entry ("Champion") with a
short description but a real mined feat (the true ceiling candidate).
- `retry_synthesis.py`'s sample: **excludes** "Champion" (`False`)
- `pipeline.py phase_synthesis`'s sample: **includes** "Champion" (`True`)

**Consequence:** a source retried through this path can be silently clamped to a lower
magnitude band than the main pipeline would have assigned it, and the record is then written
(via `do_merge` → `pipeline.write_record`) as if it had gone through the same method — the
`method` string on line 88-90 literally asserts "same prompt and same invariants as the main
synthesis phase," which is also false.

**Secondary divergence, same root cause** — band acceptance is also laxer than the main phase.
`synthesise()` (line 74): `re.match(r"^(M(?:10|[0-9]))\b", band)` — a **prefix** match.
`phase_synthesis` uses `clean_band()` (pipeline.py:136-139): `_CLEAN_BAND.fullmatch(text)` — a
**strict full match**. Reproduced (`/tmp/repro_band.py`): raw model output `"M5.7"` →
`retry_synthesis` accepts **"M5"**; `phase_synthesis`'s own `clean_band` rejects it as
**"unassayed"**. So the retry path can accept a decorated/malformed magnitude string the main
phase would refuse — again contradicting "byte-identical."

**Fix direction:** either import and reuse `pipeline._mined_feats` + the real chunking loop (and
`pipeline.clean_band`) directly rather than a hand-copied simplification, or drop the
"byte-identical" claim and document the deliberate divergence (there does not appear to be one —
this reads as an unintentional simplification, not a documented tradeoff).

---

### 2. HIGH — `save_side()` (line 43-47) bypasses the shared-state-file contract entirely; unhandled crash reproduced

`retry_synthesis.py` never imports `silence`. `save_side()`:
```python
def save_side(d):
    tmp = SIDE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    os.replace(tmp, SIDE)
```
This is precisely the pattern `silence.write_json`'s own docstring says was found and fixed at
"TWELVE call sites across ten modules" project-wide — a bare `open(path,'w')` + `json.dump` +
raw `os.replace`, with (a) a **fixed-name temp file** (no pid/thread suffix, so two concurrent
invocations of this script collide on the same tmp path — the exact race `write_json` was built
to close) and (b) **no PermissionError retry**, so a reader holding `SYNTHESIS_RETRY.json` open
at the wrong instant crashes the whole run instead of backing off and retrying, the way every
other shared-state write in this project does via `silence.replace_retry`.

`save_side()` is called once per retried source inside the main loop (line 155) — every source
processed is another chance to hit this.

**Reproduced** (`/tmp/repro_retry.py`): opened a test side-file for reading (simulating any
concurrent reader — the `--merge` path's `load_side()`, a second invocation, a person tailing
the file) and called the real `save_side()`:
```
save_side CRASHED with unhandled PermissionError: [WinError 5] Access is denied:
'...SYNTHESIS_RETRY_TEST.json.tmp' -> '...SYNTHESIS_RETRY_TEST.json'
```
This is the identical WinError 5 `silence.replace_retry`'s docstring describes as "the normal
case on a working machine, not an edge one," and this file has no protection against it.

**Consequence:** a long retry run (dozens of local-model calls, each real GPU time) can die
mid-run on a transient, ordinarily-tolerated condition, losing the in-progress source's result
and requiring a manual re-run — while every sibling module in this tree (`pick_model.py`,
`navtree.py`, `catalogue_codex.py`, `catalogue_web.py` per its own cited comment) already uses
`silence.write_json` / `silence.replace_retry` for exactly this file shape.

**Fix direction:** `save_side()` should call `silence.write_json(SIDE, d, indent=2,
ensure_ascii=False)` and drop the hand-rolled tmp/replace.

---

## src/catalogue_codex.py

### 3. HIGH — `load_register_index()` (line 104-112) discards the `source` field, causing live cross-source misattribution — REPRODUCED with real data

```python
def load_register_index():
    with open(REGISTER, encoding="utf-8") as f:
        reg = json.load(f)
    idx = {}
    for item in reg:
        key = norm(item.get("name"))
        if key and key not in idx:
            idx[key] = item
    return idx
```
Every item in `LOCAL_REGISTER.json` carries a `source` field (verified: `{"name", "type",
"code", "source", "desc"}`). The index key is the item's normalized **name alone** — first
occurrence in file order wins, regardless of which sourcebook it came from. The module's own
docstring (line 22-24) claims: *"Per-element descriptions are joined from LOCAL_REGISTER.json
where the **same element** was transcribed off the owner's shelf"* — "same element" is never
actually checked; only the name is.

Measured against the real register (14,576 items): **885 normalized names collide** across
different entries. Cross-checked against the *actually pending* codex/roll matchup right now
(`/tmp/repro_reg3.py`, using `parse_codex()` + the real `SWEEP_ROLL.json`): **4 live,
currently-unresolved cross-source collisions** that the next real (non-dry) run of this script
will hit:

| codex section | manifest item | colliding register sources |
|---|---|---|
| Lost Mines of Phandelver | Lightbringer | `Alpha Druid`, `Lost Mine of Phandelver` |
| Extras: The Witch Tradition | Witch | `KibblesTasty Occultist`, `Mage Hand Press` |
| Extras: The Witch Tradition | Black Magic | `Yorviing's Arcane Grimoire`, `Mage Hand Press` |
| Extras: The Witch Tradition | White Magic | `Yorviing's Arcane Grimoire`, `Mage Hand Press` |

Confirmed the actual winner for the worst case (`/tmp/repro_reg4.py`): the "Lost Mines of
Phandelver" section's canonical item **"Lightbringer"** (the module's +1 mace of Lathander) gets
attached the description *"At 18th level, you can control all of the sun's powers..."* — which
is an **Alpha Druid class feature**, entirely unrelated, because `Alpha Druid`'s "Lightbringer"
happens to appear earlier in `LOCAL_REGISTER.json`.

**Consequence:** the next real (`--write`, non-dry) run of `catalogue_codex.py` will write a
record for Lost Mines of Phandelver whose "Lightbringer" entry carries a druid class feature's
text as its description — a plausible-looking, wrong answer, indistinguishable downstream from a
correct transcription, exactly the failure shape this project's own culture (see `silence.py`)
identifies as the expensive one. It is gated behind the two-writer contract correctly
(`pipeline.write_record_catalogue`), so the mechanism of the write is fine — the content going
into that write is wrong.

**Fix direction:** scope the register index by `(source, norm(name))` and match against the
codex section's own title/source rather than a bare global name index, or at minimum detect and
report ambiguity (`len(candidates) > 1`) instead of silently taking file order.

---

### 4. MEDIUM — title-matching in `main()` (line 130-136) prefers document order over an exact match; no ambiguity detection — REPRODUCED (synthetic; 0 live collisions today)

```python
for k, t in sec_by_norm.items():
    if n and (n in k or k in n):
        title = t
        break
```
This is a substring test with no priority for `n == k` (exact match) over a looser
`n in k`/`k in n` hit, and `break`s on the first match in dict-iteration (document) order.
Reproduced (`/tmp/repro_codex4.py`): given codex sections `"Cult"` (unrelated) and `"Draconic
Cult"` (the roll source's own exact-title section), with `"Cult"` appearing first in the
document, a roll row named exactly `"Draconic Cult"` gets matched to **`"Cult"`** — the wrong,
unrelated section — even though its own exact section exists later in the same file. Once
matched, `entry_count` becomes nonzero and the roll-selection criterion (`entry_count == 0`)
means the row is never revisited, so a misattribution here is permanent.

Checked against the **real** codex (64 sections) and the real pending roll
(`/tmp/repro_codex.py`): **zero** section-title pairs are currently substrings of each other, and
**zero** pending roll rows currently have more than one candidate match. So this is not live
today, but it is a real structural defect that will silently misfile the next codex source whose
title happens to be a substring of (or contain) another section's title, with no warning printed
either way.

**Fix direction:** prefer an exact `n == k` match first; if none, require the match to be unique
among substring candidates and report (not silently pick) when it is not.

---

### 5. LOW / HYPOTHESIS — manifest line's declared count is parsed and thrown away (line 94, `parse_codex()`)

```python
for m in re.finditer(r"^\s{2,}(.+?)\s*\((\d+)\):\s*(.+?)$", body, re.M):
    etype = m.group(1).strip()
    for name in m.group(3).split(";"):
```
`m.group(2)` — the manifest's own declared item count, e.g. `Magic Item (41): ...` — is captured
and never used. Checked against the real codex (`/tmp/repro_codex2.py`): all 281 manifest lines
currently parse with `len(names) == declared`, so nothing is wrong today. But the parser has the
exact denominator available and discards it, so if a future edit to the source `.md` wraps a
long `;`-separated list across a line break (the `$` anchor stops the line-based regex at the
first newline), the count would silently drop below what the codex declares, with no signal —
the same "the file said N, we say M, and nobody checked" shape this project's own
`MIN_CATALOGUE_COVERAGE`/`MIN_HOST_COVERAGE` standards exist to catch elsewhere.

**Fix direction:** compare `len(names)` to `int(m.group(2))` and log/flag a mismatch rather than
silently accepting whatever `split(";")` produces.

---

## src/standards.py

### 6. HIGH — "sentences that survive the verbatim check" reports `holds=True` when UNMEASURED, contradicting the file's own documented rule for the identical shape — REPRODUCED

Line 699-700:
```python
out.append(_s(
    "sentences that survive the verbatim check",
    True if fab is None else fab <= MAX_FABRICATION,
```
When the fabrication rate cannot be computed (`fab is None` — no reader progress line, no
`dropped` count, or a parse failure), this HIGH-severity standard is marked **`holds: True`**
(passing). But `work_orders()` (line 1420-1423) is defined as *"Only the breaches, worst first —
the thing a person or a model is meant to act on"* and filters to `not v["holds"]` — so an
UNMEASURED fabrication rate **never generates a work order**, even though the order text
attached to this exact row says, in capitals: *"IF THIS READS UNMEASURED, TREAT THAT AS THE
FINDING."*

This directly contradicts the design principle the file states for the *same* situation
elsewhere in the same function. The "calls that succeed" standard (~line 415), when the sample is
too thin to judge, explicitly sets `holds=False` and says why in its own comment: *"UNMEASURED is
reported as a breach (not a quiet hold)... a standard that cannot see is not a standard that is
satisfied."* The fabrication standard was rewritten in this same run (per its own long comment
block, "Repaired run #28") specifically because it had "never run, not once" for its whole
life — and the fix reintroduces a sibling failure mode: it now runs, but when it can't measure,
it reports green instead of red, so the dispatch mechanism (`work_orders()`) that the whole file
exists to feed will never surface it. Only a person reading the full `report()` output (which
does print "ok ... UNMEASURED -- reason" for passing rows) would ever see it.

**Reproduced** (`/tmp/repro_fab.py`): fed `standards.check()` a `"corpus read"` job dict with a
progress `detail` string that parses a feats count but carries no `dropped` key (the exact
"reader logged progress but no drop count yet" case, or any process where `dashboard._read_row`
hasn't started emitting `dropped`):
```
FOUND ROW: {'standard': 'sentences that survive the verbatim check', ...,
            'holds': True, 'observed': "UNMEASURED -- the reader's progress line carried no
            `dropped` count", ...}
in work_orders: False
```

**Fix direction:** set `holds = fab is not None and fab <= MAX_FABRICATION` (mirroring "calls
that succeed"), so UNMEASURED is a breach like every other standard in this file that has
already had this exact lesson applied to it.

---

### 7. HIGH — fixed-name temp file for `state/job_progress.json` races across the two processes this file itself says both write it — REPRODUCED (mechanism)

Line 1018-1022 (inside the "jobs that are ADVANCING" block):
```python
tmp = JOB_WATCH + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(cur, f)
silence.replace_retry(tmp, JOB_WATCH)
```
No pid/thread suffix on the tmp path — the same shape `silence.write_json`'s docstring says was
audited and fixed at twelve other call sites ("the loser can replace the winner's target with a
partial file"). `standards.check()` is called from more than one live process: the file's own
comment at line ~1207-1216 states this explicitly — *"This check runs inside whichever process is
rendering the panel — `publish.py` for the public page, `dashboard.py` for the local one"* — and
both call `check()` on their own timers.

`silence.replace_retry` only catches `PermissionError`; it does **not** catch
`FileNotFoundError`. If two processes race on the same fixed tmp name, the loser's own tmp file
has already been moved away by the winner by the time the loser calls `os.replace`, raising an
**uncaught `FileNotFoundError`** that propagates out through `replace_retry` and out of this
block's own `try/except Exception` wrapper (which does catch it, but only *after* the standard's
`out.append(...)` call further down never runs) — silently dropping the entire HIGH-severity
"every running job is advancing" standard from that round's report. This is exactly the "a
standard that does not emit is worse than one that fails" failure mode the same file calls out
by name in two other places in this exact function (the fabrication standard above, and "the
library's counters are moving," line ~845-850).

**Reproduced the underlying mechanism directly** (`/tmp/repro_race.py`, using the real
`silence.replace_retry`): simulated two writers racing on the fixed tmp name — writer B wins and
moves the tmp file away, then writer A calls `silence.replace_retry` on the now-gone tmp path:
```
Traceback (most recent call last):
  File "...\src\silence.py", line 233, in replace_retry
    os.replace(tmp, dst)
FileNotFoundError: [WinError 2] The system cannot find the file specified:
  '...\state\job_progress.json.tmp' -> '...\state\job_progress.json'
```
confirming `replace_retry` does not absorb this shape of collision. (Note: this reproduction
step wrote through the real `state/job_progress.json`/`.tmp` paths to get a faithful WinError;
both files were deleted afterward — the job-watch cache regenerates itself safely on the next
`standards.check()` run with no false stall, since `job_stamp()` treats a missing previous entry
as un-held.)

**Fix direction:** give the tmp path a pid/thread suffix (`JOB_WATCH + ".%d.%d.tmp" %
(os.getpid(), threading.get_ident())`), i.e. route this write through `silence.write_json(...)`
like `navtree.py` and `catalogue_codex.py` already do, instead of hand-rolling the pre-`write_json`
pattern in a file that otherwise imports `silence` for exactly this purpose.

---

### 8. LOW — "every declared floor is measured" self-check (line ~1350-1370) is a source-grep and structurally cannot detect a dead-but-referenced constant — VERIFIED-BY-READING (self-admitted limitation, not new)

The self-check searches `check()`'s source text for a word-bounded occurrence of each declared
`MIN_`/`MAX_` name. This is a classic lens-4 shape (a check that can pass on the wrong evidence):
a constant referenced only inside an unreachable branch, or only in an f-string on a line that
never executes for the constant's own comparison, reads as "measured." The file's own comment
admits this precisely (the fabrication-standard writeup: *"MAX_FABRICATION IS named here — on a
line that could never execute... A source-grep cannot tell a used constant from an unreachable
one"*). Not a new defect I'm asserting was missed — it's already documented as a known blind spot
in the same file — but it is worth recording here because finding #6 above is a live instance of
exactly the class this self-check cannot see even after the "fix": the constant `MAX_FABRICATION`
is referenced on a reachable line, so the self-check reports "measured," while the row's
`holds` logic is nonetheless wrong. The self-check would need to become a behavioural test
(assert a known-bad input trips the standard) to close this, as `NEXT_STEPS §2` in this project's
own notes apparently already calls for elsewhere.

---

## src/pick_model.py

No correctness bugs, swallowed-failure defects, cap violations, or two-writer-contract
violations found. This module writes only `config.yaml` (not a "record"), and does so correctly
through `silence.replace_retry` with an honest boolean return the caller checks (its own
docstring documents two historical bugs — a discarded `replace_retry` boolean, and a no-op
`re.sub` reported as success — both now fixed and covered by the return-value check at line
129-133 and the `n == 0` guard at line 120-123). `FAMILY_TIERS` substring-matching order was
checked by hand for a shadowing hazard (e.g. `"llama3"` vs `"llama3.1"`, `"phi3"` vs `"phi3.5"`)
and is safe: longer/more-specific family strings all sit in a strictly higher-or-equal tier and
the tier lists are walked highest-tier-first, so a longer match is always tried before the
prefix it would otherwise fall into. No `[:N]` truncation touches the actual model list; the
one `min(size_score, 6)` cap is a deliberate, documented scoring-formula clamp, not a data cap.

One cosmetic-only note, not raised as a finding: `silence.note("pick_model.py:150")` at line 211
(inside `free_vram_gb`) — the numeric suffix no longer matches that function's actual line
number after edits. It's a free-text label used only for the failure ledger's grouping and costs
nothing functionally, but a future grep for "pick_model.py:150" to find this handler by line
number would land in the wrong place.

Ran the module live against the real Ollama daemon and this machine's card (10GB total, 343MB
free at the time): it correctly reported `qwen3:8b` as resident-eligible under the GPU-only
ruling (total-VRAM-based budget, 9.0GB) while flagging it "WILL OFFLOAD" in the same line's
`fit_note` (current-free-VRAM-based, 0.3GB free). Both numbers are independently correct and the
dual view is intentional per the module's own documented rationale (residency gate uses *total*
capacity so it isn't noisy against whatever else is using the card at the instant of the check;
`fit_note` uses *free* capacity because that's what a call made right now will actually
experience) — flagged here only so the supervisor doesn't mistake the two different-looking
numbers for a bug; they are not.

---

## src/navtree.py

No correctness bugs, swallowed-failure defects, cap violations, or two-writer-contract
violations found. Confirmed (by reading, cross-referenced against the module's own changelog
comments) that all three historical bugs the module's docstring exists to prevent are actually
fixed in the current code: sources get nodes even with zero worlds (`touch()` called
unconditionally in the sources pass), world lists carry no `[:N]` cap ("No cap: a universe lists
every world it holds" — verified true, line 99-109), and the hyperverse/register naming
tie-breaks are deterministic (`m41` fix: `max(set(...), key=lambda x: (count, x))`, not the
hash-order-dependent `max(set(...), key=count)` that used to rename nodes between runs). The
`sources_under()` substring-matching fix (m11, the `+ "."` boundary fix) is present and correct.
Writes go through `silence.write_json` (atomic, pid/thread-suffixed tmp), gated on a clean
`audit()` first — the `problems[:6]` slice in `main()` is display-only; the actual gate
(`if args.write and not problems`) checks the full, untruncated list.

One minor completeness gap, not a bug in current output: `audit()` (line 210-223) cross-checks
that a node's world count (`n`) equals the sum of its children's world counts, and that leaf
world-lists match their claimed count, but never performs the equivalent rollup check for `src`
(source count) against children — so a hypothetical future defect in the source-rollup path
(`nd["src"] += 1` at each of the three source-tier levels) would not be caught by this audit the
way an equivalent world-count defect would be. Recorded as HYPOTHESIS since no such defect exists
today.

---

## Summary table (all findings, worst first)

| # | Severity | File:line | Status |
|---|---|---|---|
| 1 | HIGH | retry_synthesis.py:56-67, 74 | REPRODUCED |
| 2 | HIGH | retry_synthesis.py:43-47 | REPRODUCED |
| 3 | HIGH | catalogue_codex.py:104-112 | REPRODUCED (live data) |
| 4 | HIGH | standards.py:699-711 | REPRODUCED |
| 5 | HIGH | standards.py:1018-1022 | REPRODUCED (mechanism) |
| 6 | MEDIUM | catalogue_codex.py:130-136 | REPRODUCED (synthetic) |
| 7 | LOW | catalogue_codex.py:94 | VERIFIED-BY-READING / HYPOTHESIS |
| 8 | LOW | standards.py:~1350-1370 | VERIFIED-BY-READING |
| — | none | pick_model.py | clean |
| — | none | navtree.py | clean (one HYPOTHESIS completeness gap noted) |
