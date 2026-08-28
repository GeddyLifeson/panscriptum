# AUDIT — batch 08 — run #36

Modules: `magnitude.py`, `allsweep.py`, `secondopinion.py`, `pick_model.py`, `entity_match.py`,
`render.py`, `snapshot.py`, `roll.py`

All eight read in full. Findings verified by direct execution against the live source (not
inferred from docstrings), per the sweep's own discipline.

---

## magnitude.py (1398 lines)

### MAJOR — Guard 3 (subject/DOER check) is real and CAN refuse, but it is only wired into the
one-shot path. The split path — which is the DEFAULT for the heaviest, best-documented entities
— never calls it, and the mining stage does not screen for the failure it exists to catch.

The specific guidance for this batch asked whether "the entity must be the DOER" guard can ever
reach its refusal. It can, and I verified all four documented refusal shapes against the live
`subject_refusal()` function directly:

```
subject_refusal("Goku", "The universe was destroyed by Beerus in a single blow.", "ruin")
  -> "the deed is credited to Beerus"                                  (case a, passive+agent)
subject_refusal("Goku", "Goku used the button to summon Future Zeno, who immediately
  proceeded to erase the rogue Kai.", "transgression")
  -> "the deed passes to Future Zeno"                                  (case c, handoff)
subject_refusal("Goku", "Beerus erased the universe with a flick of his finger.", "transgression")
  -> "Beerus leads the act and Goku is not named"                      (case d, rival leads verb)
```

Self-credit ("Goku destroyed the planet with a single punch.") correctly returns `None` (passes).
So the 2026-08-26 fix described in the module docstring (lines 32-39, 206-230) is real: this is
**not** a check that cannot fail. Confirmed also that `verify()` (the one-shot gate, called at
line 593) is the *only* caller of `subject_refusal` anywhere in the file —

```
grep -n "subject_refusal" src/magnitude.py
  39:  ... see the note above `subject_refusal`.
  338: def subject_refusal(entity, text, ax=None):
  593:     why = subject_refusal(entity, text, ax)
```

But `_split_gate()` (lines 828-846), which grades every axis scored through `_split_assay()`,
does **not** call `subject_refusal` at all — it only checks that the score is numeric and that
the citation is verbatim-contained in that axis's own candidate list:

```python
def _split_gate(got, cand):
    """Verbatim + relevance gate for split-path sheets. Axis-relevance is by construction
    (each axis was scored only from its own candidate list); verbatim is checked against that
    same list."""
```

The docstring claims relevance is "by construction" (true — `candidates()`/`feats.by_axis` bins
sentences per axis using `AXIS_LEXICON`/`_AXIS_ACT_RE`) but says nothing about subject-safety,
and it is not true by construction for that guard. I confirmed this empirically: `feats.by_axis`
filters out passive-with/without-agent sentences (`P._PATIENT`), which incidentally screens out
cases (a)/(b) above, but does **nothing** for the handoff (c) or bystander-leads (d) shapes —
the exact shapes the docstring names as the ones the old guard could never catch:

```
feats.by_axis("Beerus erased the universe with a flick of his finger, ending the story arc
  on Goku's page.", "dragonball.fandom.com/Goku")
  -> {"ruin": [...that exact sentence...], "transgression": [...that exact sentence...]}
```

That sentence — Beerus's deed, mined verbatim from Goku's own wiki page — passes cleanly into
Goku's per-axis candidate list. `assay_entity()` sends any entity whose one-shot prompt exceeds
`ONE_SHOT_MAX` (30,000 chars) through `_split_assay`/`_split_gate` **by default** (line ~875:
"Big evidence goes through the per-axis split by default"), and the module's own docstring
names Jace Beleren, Goku, Frieza, Vegeta as exactly the entities this path exists for (the
"heaviest, best-documented entities in the library", lines 656-661). So the fix to Guard 3 is
proven to work, and is proven to be absent from the path that most needs it. If a bystander
sentence like the Beerus example above is ever the strongest-scoring candidate for an axis on a
split-assayed entity, it would be credited with nothing catching it — the exact failure the
module's docstring (lines 16-23) describes as the reason the whole file is guards.

This may be an intentional trade (the split path was itself a recent rewrite to stop deferring
heavyweight entities forever, and re-running `subject_refusal` per slice would cost more calls);
if so it is undocumented as a trade-off and should at minimum be named in `_split_gate`'s
docstring the way the relevance claim already is. As it stands it reads as an oversight, not a
decision — nothing in the file says split-path sheets accept weaker subject-safety than
one-shot sheets.

### MINOR / verified fixed — Guard 1 (verbatim / empty citation)

Tested directly: an axis scored with `"feat": ""` now correctly returns `rejects=[('ruin', 'no
citation given')]` and `scores['ruin'] == A.UNESTIMABLE`, matching the documented 2026-08-26 fix
(lines 557-577). Not a defect.

### Read, nothing else found
`saturated()` (guard 4, >=6 axes at >=9.0), `quantity_scores()` (guard 5), `candidates()`
(uncapped per Hard Rule 0 — confirmed no `[:cap]` slice unless `cap` is explicitly passed, and
nothing in the file calls `candidates()` with a `cap`), `compose()`'s round-robin budget
allocator, `settled()`, `run_batch()`'s Windows-replace retry and worker-ceiling handling, and
`calibrate()`'s checkpoint/resume logic all read correctly and match their docstrings. The
`_BAD_CHARS` corruption self-check at the top of the file is real (raises `SystemExit` if any of
the four control characters appear in the file's own source).

---

## allsweep.py (606 lines) — today's rewrite

### Verified: `_row_is_fault` fails closed and rows are NOT currently born ungradeable.

```python
def _row_is_fault(row):
    return bool(row.get("bad", True)) if isinstance(row, dict) else True
```

A non-dict row, or a dict with no `bad` key, is graded a fault by default. I checked every
`note()` closure in `estate.py` (the sole producer of ESTATE rows) — `charter()`, `written()`,
`terminal()`, `external()` each define their own local `note(finding, detail="", bad=False)` and
every one of them writes `"bad": bool(bad)` unconditionally into the row:

```
src/estate.py:189:  out.append({"finding": finding, "detail": str(detail), "bad": bool(bad)})
src/estate.py:270:  out.append({"finding": finding, "detail": str(detail), "bad": bool(bad)})
src/estate.py:322:  out.append({"finding": finding, "detail": str(detail), "bad": bool(bad)})
src/estate.py:358:  out.append({"finding": finding, "detail": str(detail), "bad": bool(bad)})
```

And every `out.append` in all four functions goes through that local `note()` — I grepped for
stray `out.append` calls that bypass it and found none. So today, no row from `estate.py` can
arrive ungradeable; `_row_is_fault`'s "fail closed on unknown" branch is currently dead-but-safe
defensive code, not a gap. `allsweep.main()`'s own crash handler for a tier that raises also sets
`"bad": True` explicitly (line 527). `estate_faults()` sums across all four `ESTATE_TIERS` and
`main()`'s `bad` count now includes `len(est_faults)` (line 589) alongside imports/lint/verify —
so `MASTER CHARTER MISSING` (an `E.charter()` finding with `bad=True`) would now correctly fail
the sweep's exit code, closing the hole the module's own docstring (lines 396-406) describes:
before this rewrite `main()` summed only `estate["artifacts"]["bad"]` and none of the four
named-fault tiers.

I did not find a way, reading the current call graph, to produce a row that reaches
`estate_faults()` without a `bad` key. This is a genuine fix, not a partial one.

### Observation, not a defect — `NEVER_RUN` is confirmed inert
`grep -rn "NEVER_RUN" src/*.py` shows it referenced only where it is defined and commented; its
own comment says "NOTHING READS NEVER_RUN; it is a roster for a human to check against, not a
gate" — that claim is accurate. Flagging only because an unread roster is exactly the shape of
finding #3 in the sweep brief ("safety with no caller"), but here it never claimed to be a gate
in the first place, so it's a QUESTION (should this become a real gate against `modules()`?)
rather than a defect.

### Read, nothing else found
`check_import`'s halt-refusal / no-traceback / SystemExit handling (lines 128-170), `reconcile()`'s
seven independent cross-checks, the atomic `silence.write_json` landing of `ALLSWEEP.json`, and
the LINT tier's pyflakes invocation and grading all read correctly.

---

## secondopinion.py (456 lines)

### Measured (not just read) what `NOT_FILED` actually waives, per the batch guidance.

Ran the exact ruff selection this module uses against `src/`:

```
ruff check --select "E,F,B,BLE,S110,S112,PLE,PLW,RUF,SIM" --ignore "E501,RUF001,RUF002,RUF003" src
  total findings: 1014
  waived (NOT_FILED) total: 401  (39.5%)
    SIM115  184  WAIVED
    E402     84  WAIVED
    PLW1510  30  WAIVED
    B007     26  WAIVED
    RUF059   22  WAIVED
    PLW0603  21  WAIVED
    RUF100   21  WAIVED
    PLW2901  11  WAIVED
    B008      2  WAIVED
  --- NOT waived, still in the queue ---
    BLE001  538   <- more than half of ALL findings
    S110     21
    S112      8
```

So today's `NOT_FILED` waives 39.5% of the outside opinion's findings by volume, but the
codebase's own worked example of what a *dangerous* waiver would look like — BLE001/S110/S112,
the blind-except and security codes — is confirmed still live and un-waived, consistent with the
docstring's account of the 2026-08-25 add-then-revert (lines 152-177). I spot-checked several
`SIM115` sites (the largest waived category, 184 instances) and they are consistently single-
expression `open(path).read()` / `json.load(open(path))` idioms whose handle is released by
CPython's refcounting the moment the expression completes — not resource leaks. The stated reason
text ("explicit open/close is used where a handle outlives one block") describes a different
shape than most of the sampled instances (an inline `open().read()` doesn't "outlive" anything);
the practical waiver is still defensible, but the written justification doesn't quite match the
evidence for the majority of sites. Worth a wording pass, not a safety issue.

### MINOR — a comment's own arithmetic doesn't check out

```
# The cost was measurable: 531 BLE001 + 63 S110/S112 sites out of 1,002 live findings, so the
# outside opinion would have gone on reporting while 96% of what it selects never reached the
# queue.
```
(lines 169-171). 531 + 63 = 594; 594 / 1,002 ≈ 59%, not 96% — and the complement (what *would*
have reached the queue) is 1,002 − 594 = 408, i.e. ≈41%, not the other reading of 96% either. This
is a historical comment about a same-day reverted change (not active logic — the waiver it
describes is confirmed absent from the current `NOT_FILED` above), so it costs nothing
functionally, but it's exactly the "hardcoded counts that have drifted / contradict the numbers
next to them" class the sweep brief asks about. Worth a one-line correction next time this
section is touched.

### Read, nothing else found
The `_ruff`/`_vulture`/`_detect_secrets` returncode handling (each documented and dated against a
real measured run on this machine, 2026-08-27) correctly distinguishes "ran and found nothing"
from "never ran" from "ran and errored" — `ran_clean()` requires `status == "RAN"` from every
tool, so an absent tool cannot read as clean. `mine_says()`'s scope-matching fix (comparing
`publish.scan_for_secrets` against the same root `detect-secrets` was pointed at) reads correctly.

---

## pick_model.py (359 lines)

Read in full; no defect found. `save_config()`'s atomic replace via `silence.replace_retry` (with
its return value checked, not discarded) and `resident()`'s GPU-only VRAM gate both work as
documented. One thing worth naming as a QUESTION rather than a defect: `resident()`/the REFUSED
list is computed against `total_vram_gb() - VRAM_RESERVE_GB` (capacity-based), while `fit_note()`
(the per-model annotation shown next to each *scored* model) is computed against
`free_vram_gb()` (moment-based) — so a model that passed the structural residency gate can still
display "WILL OFFLOAD" if something else is using VRAM right now. This is consistent with the
two functions' own docstrings (one is explicitly about the class of model, the other about the
current moment) and isn't a bug, but it can look like a contradiction in the printed report (a
model listed as usable, annotated as will-offload) if not read carefully.

---

## entity_match.py (296 lines)

Read in full, and every claim in `verify_math.py` §19r that pins this module's contract was
re-run directly against the live code (not just read) and all passed:

```
qualifier_compatible("Wally West (New Earth)", "Wally West (Prime Earth)") -> (False, 'qualifier-conflict')
qualifier_compatible("Wally West (New Earth)", "Wally West (Earth-16)")    -> (False, 'qualifier-conflict')
qualifier_compatible("Zangetsu (Zanpakutou spirit)", "Zangetsu")           -> (False, 'qualifier-missing')
qualifier_compatible("Wally West (New Earth)", "wally  west (NEW EARTH)") -> (True, None)
qualifier_compatible("X (Earth-2)", "X (Earth 2)")                        -> (True, None)
candidates() key-shape identical across empty-name / empty-pool / normal  -> True
similarity("Son Goku", "son-goku")                                        -> 1.0
best("Kratos", [{"name": "Kraven"}])                                      -> (None, 'no-candidate')
candidates("A", <50 items>)["truncated"]                                  -> False   (no cap by default)
```

No defect. This module is honestly self-described as not yet wired into any pipeline (`grep`
confirms `liveness.py` and `tempus.py` only reference it in prose/comments, `verify_math.py`
imports it only for the drill-style contract checks above) — a documented seam, not a hidden gap.

---

## render.py (252 lines)

Read in full; no defect found. `TIER_ORDER`/`DRAWN`/`FETCHED` split is exhaustive and `view()`
covers all nine tiers, raising `ValueError` on an unrecognized one rather than silently doing
nothing. `children_of()` is uncapped and its "gate on whether the tree charts the child, not on
a hardcoded schema" design is explained and matches Hard Rule 0's ranking-not-truncating spirit.
The `WS.build_all(limit=1)` call in `main()` is demo/sample plumbing (grabs one representative
world to render across every tier for the CLI report), not a truncation of a real roster or
report — does not implicate Hard Rule 0.

---

## snapshot.py (210 lines)

Read in full, then exercised directly (not just read) to confirm the guard actually refuses:

```
before("test-label", ["somedir"])  -> snapshot id
verify(sid)                        -> (True, "1 path(s) restored and byte-identical")
# then simulated a restore that silently drops one file inside the snapshotted directory:
verify(sid)                        -> (False, "inside somedir: restore omitted b.txt")
```

Confirms the run33 fix described in `_dir_matches()`'s docstring (lines 97-104) is real: `verify()`
does walk directory contents byte-for-byte via `_dir_matches`, not just check
`os.path.exists()` on the directory path, so a restore that drops or corrupts a file inside a
snapshotted folder is caught. `before()` raises `SnapshotFailed` (not a falsy return) both on a
copy exception and on an empty "took" list, so a caller cannot mistake a failed or empty
snapshot for a real one. One note, not a defect: `_manifest.json` is written with a plain
`open(...).write`/`json.dump`, not through `silence.write_json`'s atomic temp+rename pattern used
elsewhere in this project — but any resulting truncated manifest is still safely caught by
`manifest()`'s callers (`verify()` and `listing()` both catch the read exception rather than
trusting a corrupt file), so this doesn't reach the "discarded verdict" failure class.

---

## roll.py (144 lines) — the rows= destructive-write fix

Specifically tasked with checking this. Ran the exact scenario `drill.py`'s own net
(`_rows_kwarg_does_not_write_the_real_roll`, around line 2442) attacks, independently:

```
R.ROLL pointed at a throwaway file holding {"Real Source": "catalogued", entry_count: 900}
R.exclude("Scratch", "test reason", rows=[{"name": "Scratch", ...}])
  -> file on disk: UNCHANGED (still the canonical "Real Source" row)
  -> return value: True   ("your copy changed", not "it landed" -- per the function's own
     documented contract, since a caller who supplies rows is responsible for persisting it)
R.exclude("Real Source", "the ordinary path still persists")   # no rows= kwarg
  -> file on disk: UPDATED (status flipped to "out-of-scope")
  -> return value: True
```

Both properties hold. `exclude()` now writes `ROLL` **only** when `rows` was not supplied by the
caller (`caller_supplied = rows is not None`, `if caller_supplied: return True` without a write,
vs. the `else` branch which calls `silence.write_json(ROLL, rows, ...)` and returns its actual
verdict rather than a hardcoded `True`). This is exactly the two-part fix the module's own header
describes (lines 91-104): the destructive bug was that `rows=` changed read behavior but not
write behavior, so supplying test rows "to avoid touching the real roll" was precisely how the
real roll got overwritten twice on 2026-08-26. Confirmed fixed and in force. `exclude()` still has
no callers anywhere in `src/` outside `drill.py`'s own test harness (grepped), consistent with its
docstring calling itself "a hand-run curatorial tool."

`in_scope()`'s fail-open behavior on an unreadable roll (lines 70-79) is a deliberate, named
design choice (an unreadable roll must not silently exclude the whole library) — flagging as a
QUESTION for the record, not a defect: it is the one place in this project's safety layer that
intentionally fails open rather than closed, and the reasoning given is sound (the alternative is
worse), but it is worth knowing this module is the exception if anyone is auditing "does
everything here fail closed."

Read, nothing else found in `load()`, `out_of_scope()`, or `main()`.
