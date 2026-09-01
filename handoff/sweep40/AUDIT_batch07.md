# Sweep 40 — Batch 07 audit

Modules: `src/mutate.py` (1,798 lines), `src/silence.py` (762 lines), `src/threads.py`
(599 lines), `src/autostart.py` (489 lines), `src/burgs.py` (401 lines),
`src/retry_synthesis.py` (322 lines), `src/recover_folder_records.py` (283 lines),
`src/audit.py` (226 lines). All eight read in full, sequentially (no sampling), ~4,880 lines
total.

## Context

Every one of these eight modules is extremely heavily self-audited already: each carries
long, dated comments recording specific past defects (tautological checks, fail-open gates,
discarded write verdicts, silent truncations, RMW races) that were found and fixed, usually
by a named prior sweep or "order" id. `mutate.py` in particular is the mutation-testing
engine itself — the tool built to find "a check that cannot fail looks exactly like a check
that passed" — and its own history (documented in its docstrings) is a chain of exactly that
shape being found and repaired in itself.

Given that density of prior self-correction, and per the sweep's own playbook, the highest-
yield category left to check by hand is stale `file.py:NNN` line-number citations inside
comments — a defect class this codebase's own authors flag repeatedly as a recurring hazard
(see `silence.py:638-644`, which documents three separate hand-written line-number tags that
had already rotted and switched the *auto-generated* instrumentation tags to qualnames for
exactly this reason — but which, as this audit found, did not reach the hand-written prose
citations elsewhere in the tree). Every `\.py:[0-9]+` citation found in these eight modules'
comments was extracted and checked against the current content of the cited line.

`prose_gate.py`, `assay.py` and `escalation.py` are the mutation targets and may be
transiently corrupted while a mutation run is in progress, per the task brief — any citation
*into* one of those three files was excluded from verification for that reason (see Finding 5
below) rather than treated as a pass or a fail.

No source file was edited. No caps, tautologies, fail-open/fail-closed contract breaks,
discarded return values, or RMW races were found in the *live* code paths of these eight
modules — the pattern that recurred instead is stale line citations in comments, all doc-only
(no behavioural effect), all independently verified against the current source below.

## Findings

### 1. Stale cross-file citation — `silence.py:493` cites `navtree.py:297` (MINOR)

**Where:** `src/silence.py:492-494`, inside `write_json`'s docstring:

```python
    it: `navtree.py:297`, writing `data/NAVTREE.json`, which is what `build_terminal`,
    `reference` and the sweep resolve addresses through; measured, that tree is 411 KB compact
```

The claim is that `navtree.py:297` is the one live caller that passes `separators=(",", ":")`
to `write_json`. Checked against the current file: line 297 is mid-comment ("GATED, AND THIS
IS AN IDENTITY FAULT..."). The actual call is 7 lines further down:

```
src/navtree.py:304:        if not silence.write_json(OUT, data, separators=(",", ":"), ensure_ascii=False):
```

**Why it's wrong:** the cited line does not contain what the comment claims it contains — a
reader following the citation to verify the one live caller of `separators=` lands on prose,
not code.

**Remedy:** update the citation to `navtree.py:304`.

### 2. Stale cross-file citation — `silence.py:527` cites `hostcheck.py:170` (MINOR)

**Where:** `src/silence.py:526-527`, inside `write_json`'s docstring, describing the leaked-
temp-file hazard on a denied replace:

```python
        # `hostcheck.py:170` records the same litter one layer up for `replace_if_unchanged`.
```

Checked against the current file: `hostcheck.py:170` is `with open(tmp, "w", encoding="utf-8")
as f:` (inside the write-tmp try block), not a comment about litter. The actual "litter"
comment is 7-8 lines further down:

```
src/hostcheck.py:177-178:
        # `replace_if_unchanged` leaves the temp file where it is on a refusal, and litter beside
        # a shared state file is its own small fault.
```

**Why it's wrong:** same class as Finding 1 — the cited line is not the passage being
referenced.

**Remedy:** update the citation to `hostcheck.py:177`.

### 3. Stale cross-file citation — `silence.py:713` cites `chain.py:141/159` (MINOR)

**Where:** `src/silence.py:712-714`, inside `instrument()`, describing the project's
documented `silence-exempt:` marker convention:

```python
            # "silence", so it read `_ = "silence-exempt: ..."` (this project's documented
            # exemption marker, chain.py:141/159 and 48 others) as UNOBSERVED and would have
            # rewritten all fifty; and it included "note" where `_handlers` did not, so the two
```

Checked against the current file: `chain.py:141` is inside a comment about write-then-rename
("Write-then-rename, not a bare truncating open..."); `chain.py:159` is a blank line before
`def _corpus_root_state`. Neither carries a `silence-exempt:` marker. The actual markers in
`chain.py` are at:

```
src/chain.py:213:        _ = "silence-exempt: a missing or corrupt index rebuilds whole; documented safe"
src/chain.py:242:                _ = "silence-exempt: a file deleted mid-scan is simply not part of this harvest"
```

**Why it's wrong:** the cited lines (141/159) are off by 72 and 83 lines from the actual
markers (213/242) — a reader checking the claim against `chain.py` at those two line numbers
finds unrelated prose, not the exemption marker the sentence is illustrating.

**Remedy:** update the citation to `chain.py:213/242`.

### 4. Stale cross-file citation — `mutate.py:946` cites `generate.py:555-558` (MINOR, notable for its irony)

**Where:** `src/mutate.py:943-947`, inside `reap_orphans()`, in the very passage explaining
*why* this project stopped citing line numbers in comments (replacing a stale `:506-511`
citation with a positional description):

```python
        # citation here used to read ":506-511", which is the `ast.Compare` branch of
        # `_mutations` and has nothing to do with junctions; a line number inside a comment is a
        # claim nothing can keep honest, so it is named by position instead (order b2a113a33d50,
        # the same argument generate.py:555-558 makes for symbolic silence.note() tags). Check
```

The claim: `generate.py:555-558` makes the same argument for switching `silence.note()` tags
from line numbers to symbolic names. Checked against the current file: lines 555-558 are
inside the stale/pending-job counting loop of `generate.py`'s `main()` (`pending = []`;
`stale_count = 0`; `for job in jobs: ... if src not in _ev_cache:`) — unrelated to
`silence.note()` tags. The actual passage making that argument is 59-69 lines further down:

```
src/generate.py:614,622-624:
            # `generate.py:166` -- a line inside
            ...
            # kept honest by anything; the symbolic form other modules use (`workorders.py:load`,
            # `sweep_plan.py:shard-unreadable`) survives every edit above it.
            silence.note("generate.py:job-failed")
```

**Why it's wrong:** same class as Findings 1-3, but landing inside the one sentence in this
codebase that explicitly warns that "a line number inside a comment is a claim nothing can
keep honest" — the citation offered as the supporting example has itself since rotted.

**Remedy:** update the citation to `generate.py:614-624`, or (more consistent with the
passage's own argument) replace it with a symbolic/positional description instead of a line
range.

### 5. Excluded from verification — citation into a mutation-target file (INFO, not filed)

**Where:** `src/mutate.py:442-443`, inside `_col()`'s docstring:

```python
        occurrence-tracking was written. `prose_gate.py:201` is
        `re.split(r"(?m)^◈\\s", text or "")`: the marker is three bytes and one character, so
```

The pattern `re.split(r"(?m)^◈\s", text or "")` does exist in the live `prose_gate.py`, but
at line 232, not 201. Per the task brief, `prose_gate.py` is one of `mutate.py`'s three
mutation targets and may be transiently corrupted or line-shifted while a mutation run is in
progress; this citation was therefore **not** independently verifiable against a trustworthy
snapshot of `prose_gate.py` and is recorded here as excluded rather than filed as a finding.
If a batch auditing `prose_gate.py` directly (outside an active mutation run) wants to check
it, the real anchor is the `re.split(r"(?m)^◈\s", ...)` line, which read `232` at the time of
this pass.

### Also checked and found accurate (not findings, listed for completeness)

- `src/retry_synthesis.py:203` cites `pipeline.py:1157` for "SAME SHAPE AS" the `assessed_at`
  key — verified exact: `pipeline.py:1157` is
  `"assessed_at": datetime.datetime.now().isoformat(timespec="seconds"),`, matching.
- `src/burgs.py:294` cites `navtree.py:56` for "`navtree.py:56` takes the scalar `burg_count`
  and nothing else" — verified exact: `navtree.py:56` is
  `"b": p1, "nb": BG.burg_count(s, era, cond, p1),`, matching.
- `src/mutate.py:906` quotes `drill.py:4256 -> M.reap_orphans()` as what a 2026-08-27 reap-
  ledger entry recorded at the time — this is a historical quotation of a past incident
  record (dated, describing what the ledger said *then*), not a live claim about
  `drill.py`'s current line numbers, so it was not treated as a stale-citation defect. (For
  what it's worth, `drill.py:4256` today is unrelated prose, which is exactly what you'd
  expect from a dated quotation of a line number in a file that has since grown — this is the
  same rot the passage two paragraphs later explicitly names as the reason it now cites by
  position instead.)

## Everything else read and not flagged

No caps/truncations on ranking, no fail-open behaviour contradicting a fail-closed docstring
promise, no discarded return values from a load-bearing call, no read-modify-write races
without compare-and-swap, and no tautological/unreachable checks were found in the live logic
of any of the eight modules. Specifically checked and found correct:

- `mutate.py`'s lock (`_lock_acquire`/`_lock_release`/`_hold_lock`) uses `O_CREAT|O_EXCL` for
  the create and a token-verified conditional remove for the release — a real CAS, not a
  check-then-act race.
- `mutate.py`'s `_run_mutation` correctly refuses (raises) on a missing or gate-incomplete
  baseline rather than defaulting to an empty dict (the exact `base={}` defect its own
  comments describe as previously live on this entry point).
- `threads.py`'s `edge()` T5 exclusion and `verify()`'s round-tripped-graph checks are real,
  reachable checks (not tautologies against the object the builder just returned) — confirmed
  by tracing `build()` → `json.loads(json.dumps(graph))` → `verify()`.
- `audit.py`'s per-class denominators (`sources_with_synthesis` vs `entries_catalogued`) are
  correctly selected by key prefix, and its printed lists ("...and N more") are marked
  truncations, not silent ones — compliant with Hard Rule 0.
- `autostart.py`'s tri-state `supervisor_alive()` (`True`/`False`/`None`) is correctly
  threaded through `watch()` and `main()` without ever collapsing "could not tell" into
  "dead."
- `recover_folder_records.py` and `retry_synthesis.py` both correctly gate their exit codes
  on the verdict of `silence.write_json`/`roll.update_rows`/`PL.write_record` rather than
  reporting success for a write that was denied.
- `burgs.py`'s `class_histogram`/`_rank_at_or_above` rank-size arithmetic was hand-traced and
  is internally consistent; the `GENERATORS` display dict is live-consumed (not dead code, as
  its own comment notes six prior sweeps mistakenly assumed).

## Work orders filed

Four `MINOR`/`LOCAL` orders, one per stale citation (Findings 1-4). Finding 5 was not filed
per the task brief's exclusion of `prose_gate.py`/`assay.py`/`escalation.py` oddities.
