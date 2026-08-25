# AUDIT — run27 batch08

Modules read in full (every line): src/feats.py (991 lines), src/allsweep.py (469 lines),
src/tiers.py (347 lines), src/navtree.py (272 lines), src/tells.py (215 lines),
src/sweep_plan.py (161 lines). Total 2,455 lines.

---

## feats.py

### F1 — [HIGH][CONFIRMED] `discover()` caps (aplimit=500 / srlimit=50) still have no continuation (m82, known-open — confirmed still true)
`feats.py:348-361`. `discover()` requests `aplimit=500` subpages and `srlimit=50` search hits and,
if the MediaWiki response carries a top-level `continue` key, only records the fact in
`_CAP_BOUND` (351, 361) — it never follows the continuation token to fetch the rest. The counter
that was added (m82) correctly *measures* whether the cap binds, and `roll()` prints it
(feats.py:912-917), but the underlying truncation itself is unfixed: an entity with more than 500
subpages or whose search hits paginate is still discovered in part. This is a genuine Hard Rule 0
cap (unlike `discover()`'s `extra` parameter, which was already fixed to refuse silently-applied
truncation at feats.py:315-327).

### F2 — [HIGH][CONFIRMED] `api()`'s None-for-any-failure return contract collapses "request failed" and "genuinely nothing here" (this is what the batch brief calls out as "M16" / "discover()/fetch() sharing the same shape")
`feats.py:120-174` (api), `feats.py:311-368` (discover), `feats.py:427-453` (fetch),
`feats.py:732-808` (evidence_for), `feats.py:833-923` (roll).

Concrete failure scenario, traced end to end:
1. A host gets exhaustively rate-limited or otherwise fails every retry. `api()` swallows every
   error internally (404 at 156-158, 429 exhaustion at 160-166, generic exceptions at 170-174) and
   returns `None` in every one of those cases — indistinguishable from a well-formed, genuinely
   empty MediaWiki response.
2. `discover()`'s two API calls (348-349 allpages, 358-359 search) both use `(ap or {}).get(...)`
   / `(sr or {}).get(...)`, so a `None` from a hard failure is treated exactly like `{}` from a
   real "no results" response. `titles` ends up holding only the entity's own name (added
   unconditionally at line 335, before any API call).
3. `fetch()` (427-453) does the same `(d or {}).get(...)` collapse for its revisions call, so a
   failing host returns `out = {}` — no pages fetched — with no signal that anything went wrong.
4. `evidence_for()` (732-808) then writes `{"pages_read": [], "feats": [], "quantities": [],
   "gate_rejected": [], "text": {}}` to the on-disk cache (`silence.replace_retry`, 803-807) as a
   perfectly normal, successful result — and because `evidence_for()` never raised, the caching
   check at line 736 (`if cache and os.path.exists(path): return json.load(...)`) means this
   *false* empty result is now permanent: a later re-run, even once the host is reachable again,
   will just replay the cached "nothing here" without ever re-mining it.
5. In `roll()`, the `done["errored"]` counter (862-867, 872-884) was added specifically — per its
   own comment — to stop a systemic host failure from reading as "these entities simply had
   nothing." But it only increments when `evidence_for()` *raises*, and step 1-4 shows the whole
   failure path is architected to never raise: it degrades to an empty, cached, "successful"
   result instead. The entity is counted in `done["empty"]`, not `done["errored"]`, which is
   exactly the miscount the comment says the counter exists to prevent.

This is the same "signature failure" the module's own docstring describes for the wiki_page/host
bugs (an absence that is actually a miss wearing an honest-looking costume) — reproduced one layer
lower, inside the transport function itself, and made worse by permanent on-disk caching.

### F3 — [LOW][SUSPECTED, likely deliberate] `roll()`'s `--limit` truncates the job list
`feats.py:859-860`: `if limit: jobs = jobs[:limit]`. Under Hard Rule 0's letter this is a cap on
an entity list. It is reachable only via an explicit `--limit` CLI flag (949-951), analogous to
`generate.py --pilot` — an opt-in partial run for testing, not a silent default. Flagging as a
question, not a violation, since nothing hides it.

### F4 — [LOW][INFORMATIONAL] `remine()` has zero callers anywhere in `src/`
`feats.py:811-828`. Confirmed via `grep -rn "feats\.remine" src/*.py` — no hits. The function's own
comment (824-826) already says "This function currently has no callers... 2026-08-25," so this is
self-documented dead code, not a new finding, but worth the supervisor knowing it is still true.

---

## allsweep.py

### A1 — [HIGH][CONFIRMED] `check_import()` has no try/except around `subprocess.run(timeout=120)` — a hung module crashes `main()` and leaves ALLSWEEP.json stale (known-open, confirmed still true)
`allsweep.py:98-119` (check_import) vs. `allsweep.py:124-147` (run_verifier, for contrast).
`run_verifier()` explicitly wraps its subprocess call in `try/except subprocess.TimeoutExpired`
and a general `except Exception`. `check_import()` has neither. It is invoked via
`list(ex.map(check_import, mods))` at line 339-340 with no surrounding try/except in `main()`
either. If any one of the ~68+ modules hangs past 120s on `--help` (an import-time deadlock, a
network call gated behind a flag that still fires at import, etc.), `subprocess.TimeoutExpired`
propagates uncaught out of `ex.map()`, killing `main()` before it reaches VERIFY, ESTATE,
RECONCILE, or the final `silence.write_json(OUT, ...)` at line 436 — so `data/ALLSWEEP.json` is
never rewritten and silently goes stale while every downstream reader (dashboard, this very
supervisor) keeps trusting an old snapshot.

### A2 — [HIGH][CONFIRMED] `VERIFIERS` omits `hostcheck.py` and `style_audit.py` despite the module docstring claiming both are unified here (known-open, confirmed still true)
`allsweep.py:78-88` vs. the docstring at `allsweep.py:7-11`, which names "nine separate verifiers"
including `hostcheck` ("whether a wiki holds its fiction") and `style_audit` ("the prose"). The
actual `VERIFIERS` list runs preflight, silence, coverage, verify_math, thread_integrity, anchors,
audit, identity, reference — neither `hostcheck.py` nor `style_audit.py` appears. Reinforcing
detail not previously called out: `hostcheck` is *also* listed in `NEVER_RUN` (line 74), so it is
excluded from VERIFY (never invoked as a check) *and* the IMPORT-only allowlist's own comment
never explains why it's parked there instead of wired into VERIFY. Additionally, `identity.py` and
`reference.py` are in `VERIFIERS` but are not among the docstring's named nine — the enumerated
list and the code have drifted in both directions, not just by omission.

### A3 — [MED][CONFIRMED — self-documented, still open] `reconcile()`'s `note()` carries no severity, so the tier is ungraded (known-open, confirmed still true)
`allsweep.py:161-162` (`note()` signature: `finding`, `detail`, `count` — no severity) vs. the
`bad` tally at `allsweep.py:447-464`, whose own comment explicitly says this is a known,
deliberate gap ("RECONCILE DELIBERATELY DOES NOT COUNT, and that is a gap rather than a
decision... Giving `note()` a severity so this tier CAN gate is real work and is in NEXT_STEPS").
Confirmed still true; the comment is honest about the gap rather than contradicting the code, so
this is lower priority than A1/A2 but remains open.

### A4 — [MED][CONFIRMED] `NEVER_RUN` is dead code — defined but never referenced anywhere
`allsweep.py:69-75`. `grep -n "NEVER_RUN" src/*.py` returns only the definition line itself. The
comment directly above it says these modules "are still IMPORT checked; they are simply never
invoked. Naming them here beats guessing from a flag" — implying the set is consulted somewhere to
*prevent* a module's real (expensive/mutating) entry point from running. No code path in
`allsweep.py` — or anywhere else in `src/` — reads `NEVER_RUN`. Currently harmless only because
`check_import()` always calls modules with `--help` and nothing in this file ever invokes a module
bare; if a future tier were added that ran modules without `--help`, this set would be assumed
protective and would do nothing. This is a "comment claims behaviour the code doesn't have"
finding per the audit's lens 6.

### A5 — [LOW][SUSPECTED, likely deliberate] Reconcile `detail` strings truncate their example lists to 6 while `count` stays accurate
`allsweep.py:177, 181, 185, 224, 283-285`. Each of these `note()` calls joins only the first 6
example names into `detail` (`orphan_hosts[:6]`, `no_host[:6]`, `missing[:6]`, `stale[:6]`,
`examples` capped via `if len(examples) < 6`) while `count`/`over` hold the true total. The number
reported is always honest, but the persisted `ALLSWEEP.json` "detail" text — which is the
actionable part a person would use to go fix "40 catalogued sources with no host" — only ever
shows 6 of them. Borderline against Hard Rule 0's stated scope ("truncation of ... an entry
list"); flagging as a question since it may be an intentional print/preview convention (matches
the same pattern already used in `feats.py:_show()`), not obviously a bug.

### A6 — [LOW][SUSPECTED] `check_import()`'s "no CLI (imported cleanly)" reclassification could mask a real breakage
`allsweep.py:112-118`. Any nonzero exit from `--help` without the literal substring "Traceback" in
stderr is reclassified `ok=True, "no CLI (imported cleanly)"`. A module whose argparse setup
requires a positional argument before it will honour `--help` (e.g. subcommands via
`add_subparsers(required=True)`), or one that does an early `sys.exit(1)` after printing a caught
error with no traceback, would be marked healthy by this tier even though it cannot actually be
invoked. Not traced to a concrete failing module in this batch — flagging as a possible
false-negative path in IMPORT, worth a spot-check against the actual `src/*.py` argparse setups.

---

## tiers.py

### T1 — [HIGH][CONFIRMED] `deliberate_joins()` caps its own evidence list to 3 — a Hard Rule 0 violation reintroduced one function downstream of where the identical cap was just removed and called out as the worst kind
`tiers.py:271-274`:
```python
def deliberate_joins(w, shared):
    return sorted(((v, a, b, shared.get((a, b), [])[:3])
                   for (a, b), v in w.items() if v >= DELIBERATE_JOIN), reverse=True)
```
`shared.get((a, b), [])[:3]` truncates the shared-entity evidence list to 3 items. This is not a
print-time truncation — it is baked into the tuple this function *returns*, so any future consumer
of `deliberate_joins()` other than the current print loop (only caller: `tiers.py:324-326`) would
silently receive an incomplete evidence list with no signal. The keys are safe to look up (verified
against `weave.py:205-226`: `w` and `shared` are built together in the same loop with the same pair
key `(srcs[i], srcs[j])`, so `shared.get((a,b))` always matches `w`'s own key order — no ordering
bug there). What makes this worth flagging as high-value rather than routine: `weave.py:217-224`
documents removing a near-identical cap (`shared[p]` used to stop at 8 entries) and calls that
exact shape — "a cap LABELLED AS COMPLIANCE... the worst shape a cap can take, because the label is
what stops anyone looking" — found by the 2026-08-25 sweep. The same cap shape (truncating a
`shared[...]` evidence list to a small N) has reappeared one function downstream in a sibling
module, with no comment acknowledging or defending it.

### T2 — [LOW][INFORMATIONAL, likely deliberate] `main()`'s `unaddressed[:6]` print preview
`tiers.py:298`. Same low-risk "preview truncation with an accurate count printed separately"
pattern seen in `allsweep.py` (A5) — `len(unaddressed)` is printed in full at line 297 first.
Noted for consistency, not flagged as a primary issue.

### T3 — [INFO] No other bugs found
Threshold/assertion logic (`tiers.py:119-121`), `_components()` complete-vs-connected semantics
delegated correctly to `weave.py`, `xenoverse_grounding()`'s per-xenoverse pooling and Four-Hands
dissent recording, and the atomic write at `tiers.py:338-341` were all read and traced; no
correctness, swallowed-failure, or race issues found beyond T1.

---

## navtree.py

### N1 — [LOW][SUSPECTED] World records silently lose their seed/feature fields when `worldseed.build_all()` doesn't cover a `SEVENFOLD.json` world
`navtree.py:108`: `meta = seeds.get(desig, {})` — if a world designation present in
`SEVENFOLD.json["worlds"]` is absent from `WS.build_all()`'s output, `meta` silently defaults to
`{}` and the world's terminal-facing record ends up with only `{"d": desig}` — no `"s"` (seed),
`"f"` (features), `"a"` (attested axes), `"b"` (largest city), `"nb"` (burg count). No
`silence.note()` or any other signal is emitted when this happens, unlike the rest of the file's
disciplined use of `silence.note` for every other soft-failure path (65-68, 118-122, 123-128). I
did not fully trace `worldseed.py`'s `build_all()` (out of this batch's assigned modules) to
confirm whether it is guaranteed 1:1 with `SEVENFOLD.json`'s world set, so this is SUSPECTED, not
confirmed — worth a quick cross-check by whichever batch owns `worldseed.py`/`SEVENFOLD.json`.

### N2 — [INFO] Both self-documented past bugs verified genuinely fixed
- m11 (`sources_under`, `navtree.py:144-155`): both arms of the containment check now use the
  `+ "."` suffix (`path.startswith(key + ".")` and `key.startswith(path + ".")`) — confirmed by
  direct reading, matches the fix comment.
- m41 (non-deterministic tie-break, `navtree.py:157-168` and `176-180`): both `register_for()` and
  the hyperverse-naming selection now use `max(set(...), key=lambda x: (count, x))`, i.e. the value
  itself is the secondary sort key, making the tie-break deterministic and no longer dependent on
  Python's per-process string-hash randomization. Confirmed by direct reading.
- The atomic write at `navtree.py:259-267` (m100) is present and uses `silence.write_json`.

### N3 — [INFO] `build()`/`audit()` node bookkeeping traced and found consistent
The three-tier SOURCES loop (89-97) and five-tier WORLDS loop (100-109) build disjoint but
compatible contributions to each node's `"n"`, `"k"`, `"w"`, `"s"` fields; `audit()`'s two checks
(children-sum-matches-`n`, and leaf-`n`-matches-`len(w)`) correctly cover the two node shapes this
produces. No bug found here.

---

## tells.py

### L1 — [HIGH][CONFIRMED] `"not merely X but Y"` regex alternation-precedence bug, still open (known-open, confirmed still true)
`tells.py:70`:
```python
"not merely X but Y": r"\bnot merely\b|\bnot simply\b|\bnot just\b.{0,40}\bbut\b",
```
`|` has the lowest precedence of any regex operator, and none of the three phrases are grouped in
parentheses, so this compiles to three fully independent alternatives:
- `\bnot merely\b` — matches on its own, with no requirement of a following "but"
- `\bnot simply\b` — matches on its own, same problem
- `\bnot just\b.{0,40}\bbut\b` — the only alternative that actually enforces the "...but Y" tail

Concrete failure scenario: the sentence "The keep was not merely stone" (no "but" anywhere in it)
is flagged as a "not merely X but Y" structural tell by `scan()` (`tells.py:144-155`, via
`pat.findall(text)`), inflating both the per-passage hit count and any corpus-wide tell-rate
statistic derived from it, even though the sentence does not contain the reveal construction the
tell is named for and that `STRUCTURAL`'s own docstring describes (lines 18-19). The likely
intended pattern is `r"\b(?:not merely|not simply|not just)\b.{0,40}\bbut\b"`, gating all three
phrases behind the same "but" requirement. I checked every other entry in `STRUCTURAL` and
`DISCOURSE` (69-120) for the same shape (a bare top-level `|` immediately followed by a suffix
meant to apply to the whole alternation) — line 70 is the only one with this defect; all others
either use a single alternative or properly group their internal alternatives with `(?:...)`.

### L2 — [INFO] No caps, truncations, or swallowed failures found elsewhere
`scan()` runs the full pattern set over the full text every call with no sampling; `prompt_section()`'s
`wrap()` only affects console line-wrapping, not which words/phrases are included. The
escape-mangling self-check (37-40, 139-141) and the sentence-boundary anchor fix (124-134) were
both read and are correctly implemented.

---

## sweep_plan.py

### S1 — [HIGH][CONFIRMED] `_RECORD_LOCK` is a `threading.Lock`, giving zero cross-process exclusion, exactly contradicting `record()`'s own docstring (known-open, confirmed still true)
`sweep_plan.py:81` (`_RECORD_LOCK = threading.Lock()`) vs. the docstring at `sweep_plan.py:85-93`,
which explicitly describes the danger as "sixteen batches run AT ONCE and each one reports its own
coverage" doing "an unguarded read-modify-write: two batches reading the same file, each adding its
own modules, each writing back its own copy -- and the loser's modules vanish from the record" —
and claims "The lock covers this process." A `threading.Lock()` only serialises threads inside one
Python interpreter; it provides no protection at all between two separate OS processes each running
their own `python`/import of this module, which is the scenario the docstring is describing (16
*batches* running at once — batches of a sweep like this one are independent agent
invocations/processes, not threads of a shared parent). Reinforcing evidence that this is the real
calling pattern, not a hypothetical: `grep -rn "sweep_plan\." src/*.py` (excluding the file itself)
returns **zero** hits — `record()` has no caller anywhere in `src/`, and `main()`'s CLI
(`sweep_plan.py:128-133`) exposes only `--batches`, `--coverage`, and `--missing` — there is no
`--record` flag at all. The only way to call `record()` is by importing the module directly from
outside `src/` (e.g. a supervisor script, or a batch agent shelling out its own short-lived Python
process) — i.e. necessarily a separate OS process per caller, which is precisely the case the
`threading.Lock` cannot help with. The atomic write (`silence.write_json` at line 107) prevents a
*torn read* of a partially-written `SWEEP_COVERAGE.json`; it does not prevent one process's whole
read-then-write cycle from clobbering a concurrent process's in-flight update — the exact race the
docstring says was fixed.

### S2 — [INFO] `modules()`'s unreadable-file handling verified correct
`sweep_plan.py:35-62`. Confirmed the fix described in the file's own 2026-08-25 comment (an
unreadable module used to silently read as `lines: 0`, sorting last and "packing into a bin as free
weight"): the current code marks it `{"unreadable": True}` and calls `silence.note`. No cap or
truncation found in `batches()` or `missing()`.
