# Batch 10 audit — run29

Modules: `src/rigor.py`, `src/completeness.py`, `src/publish.py`, `src/entity_match.py`,
`src/runguard.py`, `src/catalogue_models.py`, `src/lognames.py`

Every line of every module was read. Method: read first, then reproduce with the miniconda
python wherever a driver script could demonstrate the behaviour rather than argue about it. Two
findings below were reproduced with concrete driver scripts (kept in the session scratchpad,
not in the repo); the reproduction transcripts are summarized inline.

---

## src/runguard.py

### FINDING R1 — CRITICAL — `claim()` is a check-then-act race with no lock; two callers can both believe they hold the exclusive maintenance guard. REPRODUCED.

`claim()` (runguard.py:98–121) does:

```
prior = read(path)                      # 105
if holder_is_live(prior): return False  # 106
...
rec = {...}                             # 111
if not _land(rec, path): return False   # 119
return True, "claimed"                  # 121
```

There is no lock, no exclusive-create (`O_EXCL`), no compare-and-swap, and no re-check between
the read at line 105 and the write at line 119. Two callers that each read a "not live" prior
(both see nobody home) will both proceed to write their own record and both return
`(True, "claimed")` to their caller. This is exactly the class of failure the module's own
docstring says it exists to prevent (bug m27 — "the effect is the exact inverse of what the guard
is for: ... two runs believe they hold the guard"), just triggered through `claim()` instead of
through `beat()`.

**REPRODUCED.** Driver: two threads in one process, synchronized on a `threading.Barrier`, both
call `runguard.claim("A"/"B", path=<fresh path>)` on the same never-before-existing guard file.
File I/O releases the GIL, so this reliably forces the same interleaving that two separate OS
processes would produce under contention. 200 trials, fresh guard path each trial:

- **94 / 200 trials (47%) produced a genuine double-claim** — both threads received
  `(True, "claimed")` on the same guard record.
- The remaining trials either single-claimed cleanly or crashed (see R2 below); a crash also
  means the guard's mutual-exclusion promise was not honoured.

Consequence: under real contention (the standing maintenance loop firing while an interactive
session also claims, which the module's own docstring treats as the normal case that motivated
its existence) two maintenance runs can proceed to do live, guarded work simultaneously, which is
the precise failure `runguard.py` was written to make impossible.

### FINDING R2 — HIGH — `_land()` → `silence.replace_retry()` only catches `PermissionError`; a losing racer gets an UNCAUGHT `FileNotFoundError`, breaking the module's explicit "does not raise" contract. REPRODUCED. (Elaborates the already-queued `_land()` fixed-name-tmp item — new consequence, not the item itself.)

`_land()` (runguard.py:72–80) writes to a **fixed-name** tmp file `path + ".tmp"` and calls
`silence.replace_retry(tmp, path)` (silence.py:223–240), which retries **only on
`PermissionError`**:

```python
def replace_retry(tmp, dst, attempts=5):
    for a in range(attempts):
        try:
            os.replace(tmp, dst)
            return True
        except PermissionError:
            ...
    return False
```

Because the tmp filename is fixed (not PID/thread-qualified, unlike `silence.write_json`'s
documented fix for exactly this hazard — see silence.py:262–265), two racing writers can both
target the same tmp path. When writer A's `os.replace(tmp, dst)` succeeds first, it consumes
(renames away) the tmp file. Writer B's own `os.replace(tmp, dst)` then raises
`FileNotFoundError`, not `PermissionError` — a type `replace_retry` does not catch. Nothing in
`_land()` or in its callers (`claim()`, `beat()`, `release()`) wraps that call in a `try/except`
either. The exception propagates all the way out of the guard API.

This directly contradicts the module's own header: **"WHY IT DOES NOT RAISE ... `beat()` returns
False and says so on stderr rather than raising"** (runguard.py:27–33), and `claim()`'s docstring
promise: **"Returns (ok, reason)"** with no raise documented. Under contention, it does raise.

**REPRODUCED** in the same 200-trial run as R1: **104 / 200 trials (52%) crashed** with an
unhandled traceback of the shape:
```
FileNotFoundError: [WinError 2] The system cannot find the file specified:
  'tguard_N.json.tmp' -> 'tguard_N.json'
```
raised from `os.replace()` inside `silence.replace_retry` (silence.py:233), called from
`runguard._land()` (runguard.py:80), called from `runguard.claim()` (runguard.py:119).

Note: R1 and R2 are two faces of the same missing lock — some interleavings produce a silent
double-claim (R1), others produce a hard crash (R2), and which one you get is scheduling luck.
Both are downstream of `claim()`/`beat()`/`release()` having no serialization primitive at all,
and R2 specifically shows the fixed-tmp-name issue already queued for owner ruling has a concrete,
previously-undocumented consequence: it is not just "a race", it can crash the caller outright
because `replace_retry`'s except clause doesn't cover the exception type this exact race produces.

### Other lens categories for runguard.py

- **Swallowed failures**: none found beyond the above. `read()`'s broad `except Exception` is
  deliberate and documented (runguard.py:55–58: an unreadable guard must not wedge the pass), and
  is logged via `silence.note`, not silently dropped.
- **Hard Rule 0 caps**: none. No `[:N]`/`limit=`/sampling anywhere in this file.
- **Checks that cannot fail**: none found.
- **Two-writer contract**: `MAINTENANCE_RUN.json` is a shared state file and IS written via
  `silence.replace_retry` (correct primitive), but see R1/R2 — using the right primitive did not
  close the race because nothing guards the read-then-decide step, and the primitive itself
  doesn't cover every exception the fixed-name collision can throw.
- **Docstring/code contradiction**: R2 is exactly this (category 7) as well as a correctness bug.

---

## src/publish.py

### FINDING P1 — HIGH — `write()` bypasses the project's two-writer contract entirely: raw `open()+json.dump()+os.replace()` on a fixed-name tmp file, with no retry, for a file the module's own docstring says has two concurrent writers. REPRODUCED (isolated harness).

`write()` (publish.py:283–290):
```python
def write(state=None):
    os.makedirs(DOCS, exist_ok=True)
    data = state if state is not None else snapshot()
    tmp = STATE_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, STATE_JSON)
    return STATE_JSON
```
`STATE_JSON` (`docs/state.json`) is precisely the file `push()`'s own docstring (publish.py:293–300)
says has two writers: *"Two writers publish into this tree (the standing loop and whatever session
is working)"*. Yet `write()` uses none of the project's established shared-file primitives:
- no PID/thread-qualified tmp name (contrast `silence.write_json`, built specifically because a
  fixed `path + ".tmp"` lets "the loser ... replace the winner's target with a partial file")
- no `silence.replace_retry` — a bare `os.replace()`, so even the ordinary Windows
  antivirus/reader-holds-the-handle case (which `completeness.land()` and `runguard._land()` both
  defend against) is unhandled here and will raise `PermissionError` straight into the caller.

The only thing standing between this and an unhandled crash mid-loop is the blanket
`try/except Exception` around the whole publish cycle in `main()` (publish.py:358–372), which
does catch it — so the practical effect of a collision is "publish failed: PermissionError: ..."
printed and the whole cycle (sync_tree + render_page + write, already completed for this
iteration) thrown away, to be retried next loop tick. That is a *quieter* failure than
runguard's (see R2) only because of that outer catch-all — the underlying defect (fixed-name tmp,
no retry) is the same shape and is a straightforward two-writer-contract violation: this file
should be landed via `silence.write_json` or at least `silence.replace_retry`, exactly like every
other shared JSON file in this project now does.

**REPRODUCED (isolated harness, not the live file):** wrote a driver that reimplements exactly
`write()`'s open/dump/replace sequence against a scratch path, with two OS processes writing
large (~200KB) payloads in a loop targeting the same fixed tmp name. Result: one process hit
```
PermissionError: [Errno 13] Permission denied: 'out\state.json.tmp'
```
on the bare `open(tmp, "w")` call — unhandled inside the writer itself, exactly matching what
`publish.write()` would do with two real overlapping publish invocations. (This was run against
a throwaway harness file, not `docs/state.json`, per the "never touch panscriptum-export" and
"don't edit src/" constraints — but the code under test is a line-for-line copy of `write()`'s
logic.)

### FINDING P2 — LOW — `render_page()` writes `docs/index.html` with no atomicity at all (not even a tmp+rename), under the same two-writer conditions `push()` documents. VERIFIED-BY-READING.

`render_page()` (publish.py:244–264) does a direct `open(PAGE, "w").write(html)` — no tmp file,
no rename. Under the documented two-writer scenario, a reader of `docs/index.html` (git add
reading the file to hash it, or GitHub Pages serving it) landing mid-write can see truncated
HTML. Lower severity than P1 because the page is fully regenerated from a deterministic template
every cycle (nothing here is a read-modify-write, so there's no data-loss vector, only a
transient-truncation vector), but it's the same "shared file written outside the project's atomic
primitives" pattern as P1, in the same function's neighbourhood.

### Other lens categories for publish.py

- **Swallowed failures**: none beyond documented, logged (`silence.note`) catches — e.g.
  publish.py:173 (`standards.check` optional), publish.py:337 (best-effort rebase abort).
- **Hard Rule 0 caps**: none on data. `push()`'s commit-message summarizer
  (`sorted(code)[:6]` + `"+N more"`, publish.py:322–323) and the `RuntimeError` message
  truncations (`[:220]`, `[:120]`, `[:180]`) are all **display-only** — they shorten
  human-readable text, never the underlying git operation (which still stages/commits every
  changed file) or the written JSON. Correctly non-issues.
- **Checks that cannot fail**: none found. `_is_throwaway`/`export_root` are exercised by real
  environment values, not tautologies.
- **The known, already-queued item** (`publish._scrub()`'s narrow 8-prefix credential match) was
  not re-derived. Nothing else credential-shaped was found nearby it.
- **Minor, not filed as a finding**: `push()`'s commit-message classifier
  (`p = ln[3:].strip().strip('"')`; `p.startswith("src/") and p.endswith(".py")`) will
  misclassify a `git status --porcelain` rename line (`R  old -> new`) as "other" rather than as
  a code file, which only affects the cosmetic commit-message text, not what actually gets
  committed. Too low-stakes to rank as a finding.

---

## src/rigor.py

### FINDING G1 — MEDIUM — `bradley_terry()` nulls `strengths` on refusal but leaves `deviance`/`deviance_per_df` populated from the very (invalid) `p` it just refused to report. REPRODUCED.

The function computes `p` via MM iteration, then computes `dev`/`df` from that `p`
(rigor.py:399–417), builds `out = {..., "strengths": p, "deviance": dev, "df": df, ...}`
(rigor.py:419), and only *afterward* checks Ford's condition / undefeated-winless and, on
refusal, sets `out["strengths"] = None` (rigor.py:445–446, 452–453) — but never touches
`out["deviance"]` or `out["deviance_per_df"]`.

The module's own stated philosophy is that an unidentified/unbounded `p` is not an estimate at
all — *"the true maximiser is at infinity and no finite answer exists"* / *"the iteration cap
wearing the costume of an estimate"* (rigor.py:334–345, rigor.py:‑refusal text). That reasoning
applies exactly as much to a deviance figure computed from that same disowned `p`, but the
refusal only removes `strengths`, not `deviance`. The `note` field present on every returned
dict — *"high deviance per df = intransitive contests = chord, not ladder"* — reads as an
invitation to use `deviance_per_df` diagnostically, including on a refused (non-identified) row,
where it is exactly as much an artifact of "wherever the iteration happened to stop" as the
`0.998` example the docstring calls out by name.

**REPRODUCED:**
```
wins = {('a','b'):3, ('b','c'):3, ('a','c'):3}
r0 = rigor.bradley_terry(wins, prior=0.0)
r0['identified']  -> False   (graph is a→b→c→ chain, not strongly connected — correct refusal)
r0['strengths']   -> None    (correctly refused)
r0['refusal']     -> "comparison graph is not strongly connected: 3 components ..."
r0['deviance']          -> 0.008022907561110893   (NOT nulled)
r0['deviance_per_df']   -> 0.008022907561110893   (NOT nulled)
```
A caller that checks `strengths is None` before trusting the ranking (as the module clearly
intends) but reads `deviance_per_df` unconditionally (as the `note` field invites) receives a
number computed from a `p` the same function just declared meaningless.

### Other lens categories for rigor.py

- **Swallowed failures / caps / tautological checks**: none found. This module is unusually
  self-auditing — several docstrings document and correct prior bugs in the same file (the
  cumulative-vs-per-rung bits confusion at rigor.py:97–101, the CR≠curl-fraction overclaim fixed
  at rigor.py:223–225, Ford's condition added at rigor.py:341–349). All displayed truncations
  (`[c[:3] for c in comps][:4]` at rigor.py:449, `mr["load_bearing"][:6]` at rigor.py:858) are
  print/message-only; the corresponding **data** fields (`components`, `load_bearing`) are
  returned in full, and `load_bearing`'s comment explicitly names Hard Rule 0 as the reason it
  isn't sliced (rigor.py:717–719).
- **Two-writer / concurrency**: not applicable — this module writes nothing to shared state; it
  is pure computation plus a `main()` demo printer.
- Verified `_strongly_connected` (hand-rolled iterative Tarjan, rigor.py:257–299) against a known
  graph (one 3-cycle SCC + one isolated node) — correct.
- Ran the full module end-to-end (`python src/rigor.py`) — completes cleanly, all six sections
  print sane numbers, no exceptions.

---

## src/completeness.py

### FINDING C1 — LOW — `category_size_probe()`'s on-disk cache write uses a fixed-name tmp file shared by every `ThreadPoolExecutor` worker in the process; a race degrades to a dropped cache write, not corruption, because it's wrapped in its own `except`. VERIFIED-BY-READING.

`category_size_probe()` (completeness.py:88–116) caches to `state/category_sizes.json` via:
```python
tmp = _CS_CACHE_P + ".tmp"          # fixed name, no PID/thread qualifier
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(cache, f)
silence.replace_retry(tmp, _CS_CACHE_P)
```
`audit()` runs this function from up to `workers` (default 6) threads concurrently via
`ThreadPoolExecutor` (completeness.py:349–351), all targeting the same fixed tmp path — the same
shape of race as R1/R2 above, one process's worth of concurrency instead of two processes'. The
difference from runguard: this whole block **is** wrapped in `try/except Exception:
silence.note(...)` (completeness.py:113–117), so a `FileNotFoundError` from the same underlying
`replace_retry` gap is caught and logged rather than crashing the audit. Consequence is limited
to an occasionally-dropped cache write (that key gets re-probed live next time, bounded by the
12h TTL) — self-healing, not a correctness issue for the actual `COMPLETENESS.json` measurement.
Filed as low severity; flagging because it's the same underlying pattern as the already-queued
`runguard._land()` item, in a different module.

### FINDING C2 — LOW — `catalogued_counts()` truncates category names to 40 characters when used as a `Counter` grouping key. VERIFIED-BY-READING, currently harmless.

`catalogued_counts()` (completeness.py:145–146):
```python
for e in (j.get("entries") or []):
    c[str(e.get("category") or "?")[:40]] += 1
```
This is a Hard-Rule-0-shaped truncation on a grouping **key** (not a row cap), so it doesn't drop
entries — `total = sum(c.values())` still counts everything — but it can silently merge two
distinct category names that share the same 40-character prefix into one bucket in
`by_category`. Checked whether this currently bites: the only downstream consumer,
`audit()`'s `k.startswith("Persons")` (completeness.py:314), works fine because `"Persons"` (7
chars) fits well inside any 40-character truncated key, including the full
`PERSONS` constant string (58 chars, truncates to 40 but still starts with "Persons"). So no
live miscount today, but it is a latent trap: any future category whose full name shares a
40-char prefix with a different category (long, similarly-prefixed names) would have its counts
silently folded together in `by_category`, and `by_category` is never checked against the
per-entry total anywhere to catch that.

### Other lens categories for completeness.py

- **Swallowed failures**: `category_size_probe()` (BUGS m3, completeness.py:81–99) and
  `land()`'s empty/shrink guards (completeness.py:361–410) are both explicitly, carefully written
  to distinguish "genuinely nothing" from "could not measure" and to refuse a bad write rather
  than silently accept it. This is the strongest module in the batch on this axis — it visibly
  carries the scar tissue of at least three previously-fixed incidents (m3, m6, the 2026-08-24
  empty-write, the shrink-floor gap) and each fix is still enforced in the code, not just in
  prose.
- **Hard Rule 0 caps**: `--top` (completeness.py:414, 442–460) is explicitly a print-only
  slice — the docstring/help text says "the file always holds every row" and `land()` writes
  `rows` in full before `main()` ever slices for display. Correctly a non-issue.
- **Two-writer contract**: `land()` correctly uses `silence.replace_retry` and additionally adds
  its own shrink-floor and empty-result guards on top — this is the module doing the two-writer
  contract *right*, worth noting positively as contrast to publish.py's P1.
- **Checks that cannot fail**: none found.

---

## src/entity_match.py

No findings. This module is a pure, side-effect-free scoring/ranking library (explicitly "IT
PROPOSES. IT DOES NOT MERGE" — nothing here writes to the catalogue or to any shared file, so the
two-writer/concurrency lens does not apply).

- **Hard Rule 0**: `candidates(name, pool, limit=None)` defaults to no cap, and any truncation
  applied via an explicit `limit` sets `truncated=True` on the returned dict so a caller can never
  mistake a sliced list for the whole one (entity_match.py:174–239). This is Hard Rule 0 done
  correctly, with the flag as the safeguard.
- **Checks that cannot fail**: `qualifier_compatible()` (the module's central gate, protecting
  against the Wally-West-style continuity collapse) was checked against its own worked example
  and against a same-qualifier case — behaves as documented, and the module header itself
  documents a prior over-claim ("EXACTLY" was corrected to "identical after `_norm`") that has
  since been fixed and now matches the code.
- Confirmed the one line that looked like a possible operator-precedence bug — `mid = m.get("id")
  or m.get("name") if isinstance(m, dict) else str(m)` (catalogue_models.py:98, not
  entity_match.py, see below) — is not a bug: Python's conditional-expression grammar binds `or`
  inside the branches, so it parses as `(m.get("id") or m.get("name")) if isinstance(m, dict)
  else str(m)`, verified with a direct interpreter test.

---

## src/catalogue_models.py

No findings of note. This module is well self-audited already: its own comment at
catalogue_models.py:146–151 documents a **prior** Hard Rule 0 violation (`available_sample`
used to be `[:8]`-capped on the exact field a human reads to pick a replacement model, fixed in
run #26) and the current code returns the full model list. The one remaining truncation
(`", ".join(r["models"][:10])` at catalogue_models.py:158) is purely a console print of
alternatives, not the written record — `data/PROVIDER_MODELS.json`'s `stale[].available_sample`
carries the full list (confirmed by reading the write path, catalogue_models.py:151, 160–163).
Writes go through `silence.write_json` (two-writer contract respected, comment at
catalogue_models.py:161 explicitly names the concurrent reader, `standards.py`).

---

## src/lognames.py

No findings. 36-line constants module (log filenames + owning-process fragments for the stall
detector). No logic to audit beyond the dict literal; both `READ`/`ROLL`/... keys and `OWNER`
values were cross-checked for consistency and match 1:1.

---

## Summary table

| # | Severity | Module:line | Category | Status |
|---|----------|-------------|----------|--------|
| R1 | CRITICAL | runguard.py:98–121 | Concurrency race (mutual exclusion itself) | REPRODUCED (47% double-claim / 200 trials) |
| R2 | HIGH | runguard.py:72–80 + silence.py:223–240 | Correctness / docstring contradiction | REPRODUCED (52% crash / 200 trials) |
| P1 | HIGH | publish.py:283–290 | Two-writer contract violation | REPRODUCED (isolated harness) |
| G1 | MEDIUM | rigor.py:399–458 | Correctness (partial refusal) | REPRODUCED |
| P2 | LOW | publish.py:244–264 | Concurrency (no atomicity) | VERIFIED-BY-READING |
| C1 | LOW | completeness.py:88–116 | Concurrency race (contained) | VERIFIED-BY-READING |
| C2 | LOW | completeness.py:145–146 | Hard Rule 0 (latent, currently harmless) | VERIFIED-BY-READING |
