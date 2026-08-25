# Batch 06 — run33
Modules read: cascade_bridge.py (1271 lines), completeness.py (482 lines), prose_gate.py (348 lines), anchors.py (277 lines), coverage.py (243 lines), cachekey.py (183 lines), module_index.py (83 lines)

## PROSE GATE — explicit verdict (required by the brief's safety instructions)

**VERIFIED: `prose_gate.py` FAILS CLOSED correctly on every layer, and I found nothing to
weaken or propose opening.**

- `gate_open()` (68-87): `cfg.get("prose_enabled", False) is not True` — strict identity, not
  `bool()`. A missing key, `"false"`, `0`, `[]`, the string `"true"` all still refuse; only the
  Python literal `True` opens it. Config unreadable / not a dict -> refuse.
- `step4_gate_open()` (90-116): same strict-identity construction, plus requires
  `STEP4_PLAN.md` to exist on disk before even reading the flag.
- `evidence_ok()` (163-194): rejects a floor outside `(0, 1]` as *misconfigured* rather than
  silently admitting everything — closes the exact "floor=0 admits a zero-cited source" hole the
  incident exploited. An unmeasured source (`cited_fraction` returns `None`) refuses.
- `section_shortfall`/`assert_block_complete` (199-269): structural per-entry check (label must
  be a field, not a mentioned word; entry must carry a body of real length; missing/ghost/extra
  entries all count against the block) — this is the actual fix for `_covered()`'s old
  substring-only check that let 902/1268 entries lose their Threads section silently.
- `unearned_instrument`/`cited_names_for` (289-347): look up real mined citations through
  `cachekey.load`, fail closed to an empty set on any read error, so an axis score with nothing
  cited under it is always flagged.
- **All five layers are genuinely wired in, not just defined.** Traced every call site:
  `generate.py:304` (`assert_block_complete`), `:314-315` (`cited_names_for` /
  `unearned_instrument`), `:349` (`assert_gate_open`), `:395` (`evidence_ok`);
  `overnight.py:72` delegates to `gate_open()` directly (no second, looser reimplementation);
  `dashboard.py:505` and `drill.py:151-265` exercise `step4_gate_open`/`assert_step4_open` as
  proof. Nothing here is a gate defined but never consulted.

Did not touch this file. No loosening proposed or found.

## THE COMPLETENESS QUESTION — resolved

**"measured 0 row(s) against 1 already on disk" is NOT a bug in `completeness.py`, and it is
NOT evidence of a live empty-corpus incident.** It is the printed output of a deliberate
self-test that manufactures exactly that scenario to *prove* the SHRINK_FLOOR/emptiness guard
refuses when it should.

Evidence: `src/verify_math.py:1376-1395` builds a 1-row `COMPLETENESS.json` with
`_CP.land([{"source": "A", ...}])`, then calls `_CP.land([])` and asserts it returns `False` —
this is the exact call that prints "measured 0 row(s) against 1 already on disk... REFUSING to
overwrite." The same block goes on to seed 20 rows and re-check with 1, producing "measured 1
row(s) against 20 already on disk" a few lines later — and both strings appear together, along
with unrelated `runguard` proof lines using fake run names `runA`/`runB`/`runC`, inside
`data/ALLSWEEP.json:715-726` under the check named **"the numbers"**, which
`src/allsweep.py:87` maps straight to running `verify_math.py` as a subprocess and capturing its
stdout tail verbatim. That is the whole chain: it is proof output, not a production log.

Cross-checked against the live corpus: `data/COMPLETENESS.json` currently holds 109 real rows,
and `data/WIKI_HOSTS.json` currently lists 164 `.fandom.com`-hosted sources, none of which are
degenerate. There is no live 1-row or 0-row state anywhere on disk right now. **Verdict: correct
refusal, deliberately exercised, not a bug and not an upstream data emergency.**

## FINDINGS

### 1. completeness.py:325-358 — a source with no catalogue record on disk is reported as a normal, reliable 0%-coverage row instead of "unmeasured"  [severity: MAJOR]
`work()` looks up `rec = byslug.get(str(src).lower()) or byslug.get(...)`. If no record matches
(`rec is None` — either because this source has never been catalogued yet, or because
`catalogued_counts()` silently skipped its `records/*.json` file for failing to parse, lines
138-143: `except Exception: silence.note(...); continue`), then `got = None`, `persons = None`,
`cov = 0.0`, and the `why` computation only has branches for "no sizes/probe failure" (336-339),
"shares a host and isn't primary" (347-350), and "coverage > 1.0" (351-353) — **no branch for
"no catalogue record was found at all."** `why` stays `None`, and the function returns
`{"unreliable": None, "coverage": 0.0, "catalogued_persons": None, ...}`, which is
indistinguishable downstream from a source that really was catalogued and really does have zero
citable content.

This is precisely the failure class this module's own docstring exists to prevent one layer up
("Molecule Man... reads, from inside the library, as 'not in that fiction' rather than 'past the
cutoff'") — here it is "never catalogued" reading as "catalogued and empty." Verified dormant
right now: every one of the 164 fandom-hosted sources in `WIKI_HOSTS.json` currently has a
matching record (checked live), so no row in today's `COMPLETENESS.json` shows this shape. But
the gap is real and reachable: `CLAUDE.md`'s own "On data freshness generally" section describes
`data/` as routinely mid-flight, with sources added to the roll before cataloguing catches up —
exactly the condition that would trip this. Suggested fix direction (not applied): add a `why`
branch when `rec is None`, e.g. "no catalogue record found for this source — not yet
catalogued, or its record file failed to parse."

### 2. module_index.py:75 — MODULE_INDEX.md is written non-atomically, unlike every other persistent-state writer in this codebase  [severity: MINOR]
`with open(OUT, "w", encoding="utf-8") as f: f.write(...)` truncates the target before writing —
the "m6 pattern" this project's own comments repeatedly name as "this project's oldest species"
of bug (see `completeness.py:373-380`'s own docstring on exactly this). Every other writer I
read in this batch (`coverage.py:237`, `completeness.py:416-428`, the cache writes in
`completeness.py:112-116`) goes through `silence.write_json` or a `tmp` + `replace_retry` pair.
Low real-world stakes here — grepped all of `src/` and nothing else reads
`handoff/MODULE_INDEX.md`, so there is no concurrent-reader collision — but a crash mid-write
leaves the file truncated/corrupt with no self-healing, which is exactly the property the
project's atomic-write convention exists to prevent everywhere else.

### 3. module_index.py:2 — docstring claims "87 modules"; src/ currently holds 107  [severity: INFO]
`"""MODULE_INDEX — the map of the 87 modules, generated from their own first lines.` The number
is purely descriptive text (the actual count used at runtime is computed live via `glob.glob`,
so nothing functional depends on it), but it is stale by 20 modules (verified: `ls src/*.py`
returns 107 files today) and will keep drifting every time a module is added. Minor contract
drift — a comment describing a count the code no longer has.

## QUESTIONS

- **cachekey.py:167-183, `write_path()`.** This is a pure decision function with a known TOCTOU
  shape when a caller computes the path once and only writes much later — a previous sweep
  (`handoff/sweep32/AUDIT_batch06.md`) flagged this as BLOCKING for `read.py`'s usage (path
  computed at function entry, acted on after minutes of model calls, under a
  `ThreadPoolExecutor`). `feats.py:868` also calls `cachekey.write_path()` the same way
  (`path = cachekey.write_path(CACHE, host, name)`), but `feats.py` is not in this batch and I
  did not read the code between that call and its eventual write, so I can't say whether it
  shares `read.py`'s "long delay between decide and write" shape or writes immediately (which
  would be safe). Worth a future batch checking `feats.py` specifically for this.
- **anchors.py:242-277.** `run()`'s floor-to-ceiling invariant is *currently expected* to fail
  (`sys.exit(1)`) by explicit owner ruling recorded in the comments (2026-08-25: "obviously the
  tree holds higher," "the assay is right here for the sword vs skate guy") — the instrument's
  scores were judged correct and the hardcoded `order` list was judged wrong, but `order` itself
  was left unchanged rather than corrected to match the ruling. Is this meant to stay
  permanently red in `allsweep`, or is updating the declared `order` (or otherwise silencing the
  now-settled disagreement) still open work? I did not change anything — flagging only because a
  script whose sole job is "fail when the assay drifts" currently fails on every run by design,
  and that's worth an explicit standing sign-off rather than living as institutional memory in a
  comment.

## CLEAN

- **cascade_bridge.py** (1271 lines, read in full across two passes) — extensive, heavily
  incident-documented hardening (graded benching, per-bucket pacing, owner-exclusion list,
  transient/permanent error classification, unrecognised-failure ledger with read-side
  re-triage). Traced the failure-classification branch (unwrap -> permanent-words/status-code
  check -> transient -> unrecognised) end to end and found no inversion or gap in it. No new
  defects found.
- **coverage.py** (243 lines) — `state_of()`'s CITED > READ > NO PAGE > NOT ATTEMPTED precedence
  logic traced candidate-by-candidate across both cache bases; holds correctly in every order I
  worked through. No defects found.
- **cachekey.py** (183 lines) — `load`/`owns`/`natural_path`/`disambiguated_path` logic is
  internally consistent and matches its own docstring's claims. No defects found in this file
  itself (see QUESTIONS above for a call-site concern outside this batch).
- **anchors.py** (277 lines) — no logic defects found; the one open item is a QUESTION about
  standing behaviour, not a bug (see above).
