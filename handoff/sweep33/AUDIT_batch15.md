# Batch 15 — run33
Modules read: overwatch.py (724 lines), publish.py (597 lines), manifest_builder.py (478 lines),
estate.py (338 lines), sevenfold.py (274 lines), policy.py (226 lines), cosmology_graph.py
(159 lines), catalog.py (127 lines)

## Verification requested by the brief

**policy.py** (never audited before): checked every rule-evaluation path for a silent
permissive default. Found one real one — see Finding 1.

**publish.py** (public repo + secret scanner): verified all three required properties directly
against source.
- *A refused publish cannot return success.* Confirmed. `push()`'s `RuntimeError("PUBLISH
  REFUSED...")` (line 487) propagates out of `sync_tree()/render_page()/write()/push()`'s
  caller into `main()`'s `except Exception` (line 587), which sets `rc = 1` before returning it.
  No path swallows this into a `0`.
- *The secret scanner's suppression path reports rather than hides.* Confirmed at the
  `scan_for_secrets` level — a suppressed hit is still appended to the returned list, tagged
  `"SUPPRESSED (...)"` (publish.py:306-313), not dropped. See Question 1 for a caveat.
- *No credential-shaped value can reach the public copy.* Confirmed. The ordering in `push()` is
  correct: `scan_for_secrets(SITE)` (line 476) runs and can raise **before** `git("add", "-A")`
  (line 494) is ever called, so a leak refuses the commit, not just the push. `write()`'s
  optional `state=` parameter can bypass `_scrub()` (see Finding 3), but Lock Three
  (`scan_for_secrets`) reads the actual bytes on disk regardless of how they got there, so this
  does not open a path to the public repo.
No BLOCKING defect found against any of these three properties.

## FINDINGS

### 1. policy.py:56-58 — `is_type` silently defaults to "always true" for an unrecognized type name  [severity: MAJOR]
```python
"is_type":   lambda v, a: isinstance(v, {"str": str, "int": int, "float": float,
                                         "bool": bool, "list": list,
                                         "dict": dict}.get(a, object)),
```
If a rule's `arg` is missing (`rule.get("arg")` → `None`) or doesn't match one of the six
whitelisted names, `.get(a, object)` falls back to Python's `object` class, and
`isinstance(v, object)` is `True` for **every** value including `None`. A rule
`{"op": "is_type", "path": "x"}` written without `arg`, or with `arg` misspelled, becomes an
unconditional pass forever — exactly the "reads a field that got renamed, the comparison
becomes `None == None`, and the check reports success for ever" failure this module's own
docstring (lines 9-13) says the whole evaluator exists to catch. Worse, it is invisible to the
module's own vacuous-pass detector: `found` is `True` whenever the path resolves, so
`evaluate()`'s `vacuous` list (line 120) never flags it. Every current caller (`RECORD_RULES`
line 147, `EVIDENCE_RULES` line 163) happens to pass a correct `arg`, so this is inert today —
but it is a landmine for the next rule table, in a module whose entire design point is refusing
exactly this shape of silent defect (see the `OPS` closed-set comment at policy.py:39-41). Fix
direction: `.get(a)` with no default, raising `BadRule` when `a` is unrecognized, matching how
`check_rule` already refuses an unknown `op` (policy.py:96-98).

### 2. publish.py:470-474 — a missing `ledger_guard` module silently disables the last ledger-integrity check before a public push  [severity: MAJOR]
```python
try:
    import ledger_guard as _LG
    _LG.assert_intact()
except ImportError:
    pass
```
This is the exact anti-pattern `main()` explicitly calls out and fixes two dozen lines later for
`escalation.py` (publish.py:543-553, comment: "This used to be `except ImportError: pass`, which
meant a deleted or unparseable `escalation.py` silently switched the plant-wide halt off... Hard
Rule -1's own incident wearing different clothes"). The same file reintroduces the identical
shape for the ledger check: if `ledger_guard.py` is ever deleted, renamed, or fails to import for
any reason, `push()`'s comment at line 463-469 — "the ledgers travel with everything else, so a
truncated HANDOFF is not merely a lost relay -- it is a published one. Checked here, at the same
last moment as the secret scan" — becomes false with zero warning: no print, no `silence.note`,
no escalation. `ledger_guard.py` currently exists and imports fine, so this is latent, but it
guards against the same class of incident Hard Rule -1 was written to prevent, and the fix that
was applied to `escalation.py` a few lines above was not applied here.

### 3. publish.py:442-448 — `write()` doesn't use the project's own established safe-write pattern for this exact file type  [severity: MINOR]
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
`silence.replace_retry` exists specifically because "on Windows the rename is DENIED while any
reader holds the target open -- and this project's state files all have readers on their own
clocks" (silence.py:264-269) — and this project has repeatedly documented Norton locking
newly-written files under this exact project directory (publish.py's own docstring, lines
22-24). `overwatch.py`'s equivalent ledger/report writers (`save()` at overwatch.py:202,
`write_report()` at overwatch.py:588) both use `silence.replace_retry` for this reason;
`publish.py`'s own `write()` uses a bare `os.replace()`. A transient reader (Norton scanning the
just-copied export tree, or a person with `docs/state.json` open) raises `PermissionError`
uncaught here, which `main()`'s broad `except Exception` (line 587) catches, printing
"publish failed: PermissionError..." and skipping that whole cycle (sync + render + write +
push) rather than retrying just the write as the sibling files do. Self-healing on the next
`--loop` iteration, but a one-shot invocation (no `--loop`) would report a hard failure (`rc=1`)
for a transient lock that the established pattern elsewhere in this same codebase would have
absorbed.

### 4. overwatch.py:605-616 — a failed deep estate scan poisons `last_deep`, silently reproducing the "0 of 0 inspected" bug the file already documents fixing  [severity: MAJOR]
```python
deep = (led["rounds"] % DEEP_EVERY) == 1 or DEEP_EVERY <= 1
...
struct = structure(deep=deep)
if not deep:
    prev = led.get("last_deep") or {}
    struct.setdefault("corrupt_files", prev.get("corrupt_files", []))
    struct.setdefault("files", prev.get("files", 0))
else:
    led["last_deep"] = {"corrupt_files": struct.get("corrupt_files", []),
                        "files": struct.get("files", 0)}
```
`structure(deep=True)` (overwatch.py:335-342), when the estate scan raises, sets
`out["estate_error"]` but leaves `out["corrupt_files"]`/`out["files"]` **unset**. In `round_once`,
that `struct` still reaches `write_report` correctly on THIS round (the `estate_error` check at
write_report:555-557 shows "UNKNOWN — the artifact scan itself failed"). But the `else` branch
above runs unconditionally whenever `deep=True`, regardless of whether the scan actually
succeeded — it writes `led["last_deep"] = {"corrupt_files": struct.get("corrupt_files", []),
"files": struct.get("files", 0)}`, which evaluates to `{"corrupt_files": [], "files": 0}` on a
failed scan, silently overwriting whatever real corrupt-file count was cached from the last
*successful* deep scan. On the next non-deep round (`deep=False`, up to `DEEP_EVERY - 1` rounds
later), `struct` never even attempts the estate scan, so it carries no `estate_error` key; the
poisoned `last_deep` values get copied into `struct` via `setdefault` at lines 611-613, and
`write_report` — seeing no `estate_error` — prints "files that will not parse: **0** of 0
inspected" (write_report:558-561). This is precisely the bug the file's own comment at lines
537-548 says was found and fixed on 2026-08-25 ("a check that crashed is not a check that
passed... a clean bill of health printed by a check that never ran"), reintroduced through the
caching path the original fix didn't cover, and surfacing several rounds after the actual
failure rather than in it — the worst place for it to appear, since nobody reviewing that later
round's WATCH.md would have any reason to suspect a stale, false-clean reading.

### 5. manifest_builder.py:316-320 — any exception from `feats_index.feats_for_source` silently produces a book with zero Feats content, indistinguishable from a source with none  [severity: MAJOR]
```python
try:
    feat_rows = feats_index.feats_for_source(source_name, record)
except Exception:
    silence.note("manifest_builder.py:feats")
    feat_rows = []
```
The ~30 lines of comment immediately above this (manifest_builder.py:305-315) exist specifically
because "39,862 mined feats existed before this and no volume could print one" and because Hard
Rule 0 treats a smaller-than-real output as the central failure this project refuses to permit
silently. But the `except Exception` here catches everything — a real bug in `feats_index` (a
`KeyError` on a malformed record, an `AttributeError`, anything) produces exactly the same
observable result as "this source genuinely has no attested feats": `feat_rows = []`, no Feats
chapter emitted, and the only trace is a `silence.note()` call that nothing in this script's
console output (the `print()`s at manifest_builder.py:439-444, which report `missing_records`
and `skipped_empty` but never feats-loading failures) surfaces to the operator watching the
build. A source could silently lose its entire Feats & Attested Deeds chapter to an unrelated
bug and the manifest-build report would look identical to a legitimate zero.

### 6. estate.py:122-132 — the file-integrity sweep skips two files that publish.py actually publishes to the public repo  [severity: MAJOR (STEP4_PLAN.md) / MINOR (WATCH.md)]
```python
roots = roots or ["data", "src", "state", "output", "prompts", "reference",
                  "registry_terminal", "handoff"]
...
for f in ("CLAUDE.md", "README.md", "STATUS.md", "config.yaml", "requirements.txt"):
```
`publish.py`'s `COPY_FILES` (publish.py:134-142) sends `HANDOFF.md`, `BUGS.md`, `NEXT_STEPS.md`,
`MAINTENANCE.md`, `WATCH.md`, and `STEP4_PLAN.md` to the public repo alongside the five files
`estate.py` checks. The first four of those six are covered by `ledger_guard.py`'s stricter,
independent checks (`MIN_BYTES`, `APPEND_ONLY`, `REQUIRED_SECTIONS` — ledger_guard.py:33-36),
so that overlap is fine. But `WATCH.md` and `STEP4_PLAN.md` are in neither `estate.py`'s explicit
list nor `ledger_guard.py`'s coverage. `STEP4_PLAN.md` is the one `publish.py`'s own comment
calls "the document the owner rules on and the next run plans from" (publish.py:139-141) — a
truncation or zero-byte write to it (Norton lock, an eaten escape, a partial write) would be
published to the public repo with nothing in this project's estate/ledger apparatus ever having
opened it to check, directly contradicting `estate.py`'s own docstring claim: "every file,
opened. No sampling" (estate.py:18). `WATCH.md` carries lower risk since it is generated via
`silence.replace_retry` (overwatch.py:588), but it is still outside this sweep's stated
guarantee.

### 7. policy.py:189-194 — `main()`'s record-loading loop silently drops unreadable records with no count reported  [severity: MINOR]
```python
for p in sorted(glob.glob(os.path.join(HERE, "data", "records", "*.json")))[:a.limit]:
    try:
        with open(p, encoding="utf-8") as f:
            evals.append(evaluate(json.load(f), RECORD_RULES, os.path.basename(p)))
    except Exception:
        continue
```
A record that fails to parse is simply excluded from the evaluated set — no note, no counter, no
mention in the printed summary (policy.py:209-221). This is a smaller instance of the exact
problem this module's own docstring names as its reason for existing: "a check that cannot fail
looks exactly like a check that passed" (policy.py: header). A run against a `data/records/`
directory with several corrupt files would report a clean structural pass on the readable
remainder and never say how many records it didn't even attempt.

### 8. estate.py:198-199 — `charter()`'s exception handler mislabels failures from an unrelated subsystem  [severity: MINOR]
```python
except Exception as e:
    note("spine codes unreadable", str(e)[:80])
```
This `try` wraps three separate operations: parsing `CHARTER_SPINE_CODES.json` (line 190),
loading records via `weave_index.load_records()` (line 193), and computing the set difference
(line 194). Any exception from the second — a bug or malformed record inside `weave_index`, a
completely different subsystem — is reported to the reader as "spine codes unreadable," which
would send someone investigating a real `weave_index` fault to the wrong file.

### 9. cosmology_graph.py:68,76,94,127 — `src_entities` is computed and returned but never used  [severity: MINOR]
`build_graph()` builds a `defaultdict(int)` counting, per source, how many co-attested entities
it shares with at least one other source, and returns it as the third element of its tuple.
`main()` unpacks it (line 127) but never reads it again — it appears in no `print()` and is not
written to `SHARED_STAGE_GRAPH.json` in the `--write` block (lines 147-154). Dead output, not a
correctness bug, but worth a look: either it was meant to appear in the report/output and got
dropped, or it can be deleted.

## QUESTIONS

1. **publish.py — is a suppressed secret-scan finding actually durable anywhere, or only visible
   to a caller that inspects the raw return value?** `scan_for_secrets` does tag suppressed hits
   rather than dropping them (verified: publish.py:306-313), but the only two production callers
   (`publish.push()` line 476 and `workorders.py`'s sweep, per a quick cross-check) both filter
   suppressed items out before doing anything with the list, and neither persists the full
   (including-suppressed) list anywhere. `dashboard.py` does not reference `scan_for_secrets` or
   `SUPPRESSED` at all. The comment's claim ("visible in the audit trail, not a reason to block a
   push," publish.py:477-478) is literally true at the function-call level but I could not find
   anywhere a human would actually see a waived finding without calling `scan_for_secrets`
   directly. Would settle it: does anything write the raw (unfiltered) scan output to a report
   file anywhere, or is `drill.py`'s test the only thing that ever looks at it?

2. **manifest_builder.py:97 — `load_record`'s forward containment (`norm_target in norm_fname`)
   is not prefix-anchored the way the reverse arm was fixed to be.** I confirmed this is
   currently safe for the concrete case the surrounding comment describes ("DC" resolves to
   `dc.json` at score 0, beating `sword-coast-adventurer-s-guide.json` at score 24 — verified
   against the live `data/records/` directory). But the loophole the comment describes for the
   *reverse* direction (a short slug matching anywhere inside an unrelated long name) is
   structurally still open on the *forward* direction if a short source's own record file were
   ever missing or renamed during a re-sweep, since the closeness-ranking tiebreak only protects
   against this when a genuinely close candidate exists. Is the forward direction's free
   containment intentional (needed for the truncated-long-filename case this function was
   originally fixed for) or should it also be tightened?

3. **overwatch.py — `_STATE_RANK` (line 225) includes `"confirmed"` and `"stale"` as ranked
   states, but nothing in this file (or anywhere else in `src/`) ever sets a finding's `state` to
   either value** (`verify_open`'s confirmed branch bumps `confirmed_n` and leaves `state`
   unchanged at line 495-497). Reserved for a future manual-triage workflow, or dead entries in
   the rank table?

## CLEAN
- **sevenfold.py** — read carefully, including the affinity-order/seams/split shelving math.
  Traced through the "sources can share a top-3-tier shelfmark" behavior (e.g. Alien/Predator)
  and confirmed via the docstring (lines 47-51, 248-254) that this is explicit, intended design
  — not an address-collision bug — so I did not report it as a finding.
- **catalog.py** — read in full. No defects found; the truncated-display-with-count in
  `cmd_stats` (first 30 + "and N more") is an explicit, honest display truncation, not a Hard
  Rule 0 violation.

## Recording coverage
