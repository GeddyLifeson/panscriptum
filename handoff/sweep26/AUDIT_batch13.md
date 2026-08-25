# BATCH 13 audit — run26

Modules (line-by-line, full files, no sampling):
- `src/overwatch.py` (707 lines)
- `src/handbuilt.py` (487 lines)
- `src/onomast.py` (407 lines)
- `src/address.py` (290 lines)
- `src/hosts.py` (243 lines)
- `src/descending_ladder.py` (186 lines)
- `src/physics.py` (149 lines)

Total: 2,469 lines. Also inspected (not scored, but load-bearing on findings above): `src/allsweep.py`
(`modules()`, `reconcile()`, `check_import()`), `src/foreman.py` (`_retire`), `src/reference.py`
(`compute`, `REFERENCE`), `src/standards.py` (the "hand-built assays match the charter" check),
`src/hostcheck.py` (`candidates`), `src/silence.py` (`replace_retry`, `write_json`). Live state
inspected: `data/OVERWATCH.json` (75 rounds, 69 total findings, 0 open), `data/SWEEP_ROLL.json`
(215 sources), `data/CHARTER_SPINE_CODES.json` (219 entries).

---

## OVERWATCH.PY — why it reports 0/0/75

Verified against the live ledger (`data/OVERWATCH.json`): 75 rounds, 69 findings ever filed,
**0 currently open** — 51 `retired`, 12 `closed`, 5 `refuted`, 1 `stale`. This is real code
behavior, not a discovery gap: `allsweep.modules()` globs `src/*.py` with no filter beyond a
leading-underscore exclusion, so file discovery is complete (95 modules, all 90 non-excluded ones
appear in the ledger's `seen` map). The zero is produced downstream of discovery, by four
mechanisms, three of which are genuine defects:

**1. MAJOR — whole-file digest retires a finding on ANY edit to the file, not just an edit to the
lines it points at.** `overwatch.py:623-629`, inside `round_once()`:
```python
for fid, f in list(led["findings"].items()):
    if f.get("state") != "open":
        continue
    d = _digest(os.path.join(SRC, f["module"] + ".py"))
    if d and d != f.get("digest"):
        f["state"] = "retired"
        f["retired_at"] = led["last_run"]
```
This runs unconditionally, every round, on every open finding, with no budget — unlike
`verify_open()` a few lines later, which is throttled to `budget` (default 6) per round. The
digest is of the whole file, not the finding's line span. In a 95-module repo under continuous
editing (including by sweep batches like this one), a finding filed against a 700-line file is
retired the instant anyone touches *any* line of that file for *any* reason — a docstring fix, an
unrelated bug fix three functions away, a comment. The finding is never confirmed and never
refuted; it just disappears from "open" with no verdict, because retirement fires before
`verify_open()` gets anywhere near it (retirement loop runs first in `round_once`, unconditionally;
`verify_open` runs second, budgeted). Traced in the live ledger: 27 of 51 retirements carry
`retired_at` with no `retired_why`, consistent with this path (digest-changed, not `foreman`'s
`unactionable` tag — see #2).

**2. MAJOR — a second, unguarded writer (`foreman.py`) closes overwatch's findings out-of-band,
with no model verdict at all.** `foreman.py:1013-1038`, `_retire()`:
```python
for fid, v in (led.get("findings") or {}).items():
    if (v.get("module") == finding.get("module")
            and v.get("symbol") == finding.get("symbol")
            and v.get("state") == "open"):
        v["state"] = "retired"
        v["retired_why"] = finding.get("why", "unactionable")
```
This is called when foreman's patch lane decides a finding is unactionable — a judgment call by
that subsystem, not a re-verification of the code. It matches by `(module, symbol)`, not by
fingerprint, so it can retire a *different* finding on the same symbol than the one foreman
actually judged. It also bypasses `overwatch.save()`'s `_reconcile_with_disk` merge entirely —
it's a bare read/mutate/write with a plain `os.replace` (not `silence.replace_retry`), the exact
race `overwatch.py`'s own `save()` comments say a second writer of this ledger must not do.
Traced in the live ledger: 24 of 51 retirements carry `retired_why: "unactionable"` — this is
`foreman.py`, not the model, and not overwatch's own digest check. **24/51 retirements (35% of
everything ever filed) were closed by a subsystem outside `overwatch.py` that never asked the
model to re-look at the code.** (27 digest-retired + 24 foreman-retired = 51, exactly matching
the ledger's retired count — the math is fully accounted for.)

**3. MAJOR — `structure()`'s reconcile whitelist silently drops every "X failed" note, and
several substantive ones.** `overwatch.py:326-329`:
```python
out["reconcile"] = [r for r in A.reconcile()
                    if r["finding"].isupper() or "no host" in r["finding"]
                    or "never catalogued" in r["finding"]
                    or "MORE THAN ONE" in r["finding"]]
```
`allsweep.reconcile()` (src/allsweep.py, `note()` calls at lines 177-318) emits both severe
findings (several fully uppercase, correctly kept) and failure/informational notes in lowercase
that this whitelist does not match and therefore drops from `WATCH.md` entirely:
`"source reconciliation failed"`, `"coverage reconciliation failed"`,
`"cache reconciliation failed"`, `"purge reconciliation failed"`,
`"phase reconciliation failed"`, `"band reconciliation failed"`, `"process check failed"` — every
one of allsweep's own internal `except`-path failure notices — plus substantive findings that
happen to be phrased in lowercase: `"COVERAGE.json is stale"` (mixed case, fails `.isupper()`),
`"cache directories no source points to"`, `"purged sources that still carry entries"` (ghost
entries). This is the exact "a check that crashed is not a check that passed" defect the file's
own `write_report()` comment (lines 537-548) says was already fixed for the outer `structure()`
try/except — but the same failure mode exists one layer down, inside `allsweep.reconcile()`'s own
per-check try/excepts, and this whitelist filter reintroduces it: if `feats`/`weave_index`
reconciliation raises, `WATCH.md`'s Structure section says nothing rather than "UNKNOWN — failed".
**KEY SHAPE match**: the guard (`isupper()` or three literal substrings) matches only one spelling
of "severe finding" and every one of allsweep's failure-path notes uses a different spelling.

**4. MINOR — a module's per-slice review results are discarded wholesale on any mid-module
exception.** `review()` (line 412) has no try/except around the per-slice `_ask()` call; the only
guard is in `round_once()`, around the *entire* `review(m, ...)` call. If slice 5 of 7 raises
(e.g. a transport timeout), findings already collected from slices 1-4 in `kept` are lost — the
whole function unwinds. Not permanent data loss (the module's `seen` digest is never updated on
exception, so it's retried next round), but it means a single mid-module hiccup throws away
otherwise-good findings from that round rather than persisting them per-slice.

**5. QUESTION (latent, not currently manifesting) — an orphaned finding for a deleted/renamed
module can never retire and never get re-verified.** `_digest()` (line 213) returns `""` on any
read failure (including file-not-found). The retirement guard is `if d and d != f.get("digest")`
— empty `d` short-circuits, so a finding whose module file no longer exists is never retired.
`verify_open()`'s read (line 469-472) also fails and `continue`s *without* updating
`last_verified`, so the orphaned finding keeps sorting first ("oldest checked") and burns one of
the 6 budget slots every round without ever resolving. Checked the live ledger: no currently-open
finding points at a missing module, so this is dormant, not active — but is a real path given the
project's history of module renames.

**Net accounting**: 69 filed, 51 retired (27 digest / 24 foreman-unactionable), 12 closed
(`verify_open`'s own refutation path, the *only* mechanism that actually re-reads the current code
and gets a model verdict), 5 `refuted` + 1 `stale` (legacy state names — grep shows no current
production code path writes `state="refuted"`; only `verify_math.py`'s own unit test uses that
literal, so those 6 entries predate a rename to `"closed"` and are historical residue, not a live
bug). **Only 12 of 69 findings — 17% — were ever actually re-examined by the model and found
false. The other 44 (64%) were closed by mechanisms that never asked the model anything**: 27 by
"the file changed somewhere" and 24 by a separate module's unilateral judgment call. That is the
answer to "why zero": the closer is trigger-happy and the verifier is starved by comparison — not
because the model never finds anything (69 filed proves it does), but because almost everything
filed gets swept off the open list before its verification turn comes up.

**`_ask` failure semantics (asked to verify explicitly)**: when the local model is down or over
`CLOUD_BUDGET` (round-scoped since a 2026-08-25 fix — confirmed the counter resets at the top of
`round_once()`, line 600, so the earlier lifetime-budget bug described in that comment is fixed),
`_ask()` returns `None`, never raises. In `review()`, `(got or {}).get("findings", [])` on `None`
silently contributes zero findings for that slice — **indistinguishable from "the slice was
sound"**, exactly the blind-spot pattern the file's own header names. In `verify_open()`, `None`
produces `verdict = None`, which matches neither `"refuted"` nor `"confirmed"` — **confirmed: no
path treats "no verdict" as "refuted."** A stalled/failed verify call cannot auto-close a real
finding by itself. But `f["last_verified"] = time.time()` is set unconditionally, even when the
call failed — so a finding that keeps hitting a down/busy model gets pushed to the back of the
oldest-first queue every round it's attempted, looking "recently checked" while never actually
receiving a verdict. Not data loss, but a starvation path worth knowing about.

**Caps check**: `write_report()`'s `open_f[:40]` display slice and the `broken[:4]` /
`corrupt[:3]` summary-line slices are display-only — the printed counts (`len(open_f)`,
`len(broken)`, `len(corrupt)`) are always the true totals; nothing in the ledger or the
underlying data is truncated. Legitimate bound, not a Hard-Rule-0 violation. `rotation()`'s
`todo = (changed + stale)[:limit]` (default 6 modules/round) is documented pacing across rounds,
not a permanent drop — a module not reached this round stays in `changed`/`stale` next round
since its digest still won't match `seen`.

**Self-review gap**: `round_once()` excludes `"overwatch"` and `"allsweep"` from the model-review
rotation (line 635) — the watcher never semantically reviews its own source or its structural
scanner's source. This is presumably deliberate (avoids a self-referential dependency), but it
does mean bugs like #1-#3 above are permanently outside what this tool could ever have caught
about itself.

---

## HANDBUILT.PY

Read in full. `compute()` (line 423) genuinely recomputes every entry through `assay.assay()` —
`scores = {ax: v[0] for ax, v in rec["axes"].items()}` is read straight from the hardcoded
`ROSTER` dict and passed live into `A.assay(...)`; nothing here reads a cached/stored answer.
No bug found in `handbuilt.py` itself.

**The "hand-built assays match the charter" 3/3 standard is NOT implemented in `handbuilt.py`** —
it's `standards.py:656-681`, checking `data/REFERENCE_ASSAYS.json`, which is written by
`reference.py` (not `handbuilt.py`; `handbuilt.py`'s roster is 9 entities, not 3).
Traced it anyway since the task named it under this file's special focus:

- `reference.py:compute()` (line 215-218) does call `A.assay(...)` live, same as `handbuilt.py` —
  confirmed genuine recomputation from the `REFERENCE` dict's hardcoded axis scores, not a stored
  answer at the point of generation.
- **QUESTION/MINOR — but `standards.py`'s check itself reads a cached JSON snapshot with no
  freshness guard**, unlike its sibling check 30 lines below it in the same file
  (`CHARTER_REGRESSION.json`, which explicitly computes `age_h` and treats a stale file as a
  finding). `standards.py:656-660` opens `data/REFERENCE_ASSAYS.json` and trusts it outright. If
  `assay.py`'s scoring constants (`SIGMA_BY_ATTESTATION`, axis weights) change without someone
  re-running `python src/reference.py` to regenerate the cache, `standards.py` will keep reporting
  "3/3 — all of them" using pre-change numbers — reading a stored answer, exactly the failure mode
  the task asked me to rule out. Checked current mtimes: `REFERENCE_ASSAYS.json` (Aug 25 05:58) is
  newer than both `assay.py` (Aug 24 08:35) and `reference.py` (Aug 25 02:38), so **this is not
  currently manifesting** — but nothing in the code prevents it from going stale silently the next
  time someone edits `assay.py` without also rerunning `reference.py`.

---

## ADDRESS.PY / HOSTS.PY — shelfmark/address collisions

**`address.py`** — `spine_code_for()`'s four-tier fallback (exact → normalized → word-padded
containment → token-coverage) was ground-truthed against the live 215-source roll
(`data/SWEEP_ROLL.json`) and the 219-entry charter index (`data/CHARTER_SPINE_CODES.json`):
180 exact, 2 normalized, 17 containment, 16 coverage, 0 UNASSIGNED — **every single match
inspected by hand is correct** (Tom Clancy sub-franchises, Pantheon sub-entries, "all X" ↔ "X
(all)" pairs all resolve to the right spine code; no false collision found in production data
today).

- **QUESTION — the containment tier (tier 3) is whole-word-safe (the documented 2026-08-23 fix
  for the "DC" letter-substring bug), but the same *class* of risk exists one level up, at whole
  short-word granularity, and isn't guarded.** The index has 51 entries whose title is a single
  significant token (`data/CHARTER_SPINE_CODES.json`: `"Doom" → II.N.2`, `"Alien" → II.N`,
  `"DC" → II.D.2`, etc). A future roll addition like "Doom Patrol" (a real DC property) would
  word-containment-match `"Doom"` (id Software's spine, II.N.2) before ever reaching `"DC"`, and
  return silently — no `UNASSIGNED`, no owner-review trigger — exactly the invented-address
  failure mode Hard Rule 2 exists to prevent. Not a bug in currently-generated addresses; a
  structural gap the DC fix didn't fully close.
- Tier 4's `coverage = overlap / min(len(target_tokens), len(name_tokens))` is asymmetric by
  design (short titles can fully "hide inside" long ones at `coverage>=0.8`) but every real
  instance found in production data was a legitimate match. Flagging as the same latent-risk class
  as above, not a live defect.
- `slugify()`'s `[:60]` cap is a filename-length bound, not a data truncation — legitimate.

**`hosts.py`** — this is the module whose entire premise is "keep every host, not just the
winner," so its own caps get held to the standard it sets for everyone else.

- **MAJOR — `add()` writes the shared ledger `data/SOURCE_HOSTS.json` with the exact
  anti-pattern `silence.write_json`'s own docstring says was fixed project-wide.**
  `hosts.py:78-91`:
  ```python
  data = _load(EXTRA, {})
  rows = data.setdefault(source, [])
  ...
  tmp = EXTRA + ".tmp"
  with open(tmp, "w", encoding="utf-8") as f:
      json.dump(data, f, indent=1, ensure_ascii=False)
  os.replace(tmp, EXTRA)
  ```
  Bare read-modify-write, no merge with a concurrent writer, a non-PID/thread-qualified temp
  filename, and a bare `os.replace` instead of `silence.replace_retry`. `silence.write_json`'s
  docstring (`silence.py:250-269`) describes fixing "TWELVE call sites across ten modules" doing
  exactly this on 2026-08-25, and names the two hazards this code still has: no retry on a Windows
  `PermissionError` (a concurrent reader — the dashboard, another `hosts.py --discover` run —
  raises here uncaught, since `add()` has no try/except around the write, which would crash
  `discover()`'s whole run, not just skip one host), and a `path + ".tmp"` name that two
  same-process/same-machine writers can collide on. `data/SOURCE_HOSTS.json` is written only from
  this file (`grep` confirms), so the risk is self-inflicted concurrent runs of `hosts.py`, but
  this module's whole reason to exist is capturing evidence "the library wants both" — losing an
  addition to a lost-update race is exactly the kind of quiet, capped-without-looking-capped
  outcome the project's Hard Rule 0 is written against.
  Compounding: `_load()` (line 44-50) swallows *any* exception from `json.load` (including a torn
  read racing `add()`'s replace) and returns `{}` — a corrupted or empty read is indistinguishable
  from "no extra hosts ever recorded," the same swallowed-failure shape flagged elsewhere in this
  batch.
- **MAJOR — undocumented cap on the roster used to judge whether a host should be adopted.**
  `hosts.py:143`, inside `discover()`'s `work()`:
  ```python
  names = list(by.get(source) or [])[:40]
  ```
  No comment, no justification — in the one module in this codebase whose docstring is explicitly
  about refusing to discard evidence ("Keeps a SECOND file... Nothing here overwrites..."). Every
  host-adoption verdict (`HC.score(h, names, source, by=by)`) for a source with more than 40
  catalogued entities is judged against an arbitrary 40-name slice rather than its full roster —
  for a source with hundreds of entries, a genuinely-good secondary host whose coverage happens to
  concentrate outside the sampled 40 could be scored as not holding the source at all. This is the
  same shape of bug the project's own CLAUDE.md names as the canonical Hard Rule 0 violation
  (`roster(limit=600)` missing Goku, `cap=250` taking the alphabetical head) — a ranking-worthy
  concern turned into a silent truncation with no owner-visible flag.
- `per_source=24` (candidates-per-source cap) — checked against live data by reconstructing the
  grounded/speculative split inside `hostcheck.candidates()`: the largest grounded-only count
  across all 215 sources is 15 (`DMs Guild: Xanathar's Lost Notes to Everything Else`), so the cap
  currently only ever trims speculative subdomain guesses, matching its comment. Fragile, not
  currently broken — nothing asserts the invariant, so if a future source's "neighbour" overlap
  logic in `hostcheck.candidates()` ever pushes grounded candidates past 24, this cap would start
  silently dropping evidenced hosts and the comment claiming otherwise would go stale unnoticed.

No collisions found in `data/WIKI_HOSTS.json`/`data/SOURCE_HOSTS.json` assignment logic itself
(`hosts_for()`, `primary_host()`) beyond the write-race above — reading is straightforward and
correct.

---

## DESCENDING_LADDER.PY

Read in full, including all physics formulas. `rung_for_length()`'s no-break linear scan
(line 85-95) is correct *because* `DESCENDING`'s length column is strictly monotonically
decreasing (verified by hand: 1e6 → 1.6e-35 across all 15 rows) — the last row satisfying
`metres <= r[3]` is always the tightest-fitting band, so the unusual loop shape doesn't produce a
bug, just an easy-to-misread one. `compton_confinement_energy`, `density_at_scale`,
`schwarzschild_radius`, `binding_energy`-adjacent formulas all check out against their stated
physics (`E=p²/2m`, `ρ=m/(4/3·π·r³)`, `r_s=2GM/c²`). `transgression_bits()`'s corrected version
(the file documents its own 2026-08-20 fix) is internally consistent with its docstring.

**MAJOR — the `binding_J` column mixes two incompatible physical quantities across one table,
and the header comment asserts it's already wired to Ruin-axis scoring when nothing in the
codebase consumes it.** `descending_ladder.py:53-73`. The header states: "The characteristic
length is the rung edge for Reach; the binding energy is the rung edge for Ruin." Walking the
`binding_J` column top to bottom: Continental (1e26 J) down through Organic (1e5 J) reads as
*total structural binding energy of the whole object at that scale* — decreasing as the object
gets smaller, which is physically sound on that basis. But Cellular (1e-11) → Organellar (1e-14)
→ Macromolecular (1e-17) → Molecular (8e-19) continues decreasing, then the column **inverts**:
Atomic (2.2e-18) is *larger* than Molecular, and Nuclear (1.3e-12), Nucleonic (1.5e-10), Quark
(1.6e-10), Planck (1.956e9) climb by 20+ orders of magnitude back up. That's because rows -9
through -14 switch to *per-particle fundamental-interaction* binding energy (a covalent bond, an
ionisation energy, a nucleon's rest mass) — individually correct physics (verified: 13.6 eV
hydrogen ionisation = 2.18e-18 J matches the Atomic row; ~938 MeV proton rest energy matches
Nucleonic), but a completely different physical quantity from "total energy to unbind a
continent." A single column that means two different things depending on which half of the table
you're in cannot be used as a monotonic "rung edge for Ruin" the way the header claims — any
future code that bands or interpolates against `binding_J` across this boundary (e.g. scoring a
Ruin feat that crosses from macromolecular into atomic scale) will get a physically incoherent
answer. Confirmed by grep that **no other module currently reads `binding_J` or
`descending_ladder.DESCENDING`** (only `derivation.py`'s `SCAN_MODULES` list references the module
by name, for its own static-scan purposes) — so this is dormant, not actively producing a wrong
score today, but the header's present-tense claim that it *is* the Ruin rung edge is not backed by
any actual Ruin-scoring code path yet, and the data underneath it isn't self-consistent for that
future use.

No caps, no subprocess calls, no shared-state writes in this file — pure computation module.

---

## PHYSICS.PY

Read in full. Clean. `kinetic()`'s Newtonian/relativistic switch at `0.1c` is continuous at the
boundary (checked numerically: both formulas agree to 3 sig figs at exactly v=0.1c). `v >= C`
raises rather than returning a large number, matching the docstring's stated intent. `joules_for()`
raises on unknown material/mode rather than silently defaulting, matching its docstring.
`binding_energy()`'s `3GM²/5R` is the textbook uniform-sphere self-energy formula, correctly
implemented, and the docstring is honest about its own limitation (poor for centrally-condensed
bodies like a star) rather than overclaiming. No bugs found.

---

## ONOMAST.PY

Read in full. `well_formed()`'s four mechanical constraints (echo/stutter/cluster/consonant-density
plus vowel-run and minimum-vowel-count) were traced by hand against the examples the docstring
names as rejected (`Shiashiathasha`, `Goggoktok`, `Zgournazhun`) and all three are correctly
rejected by at least one of the six checks. `coin_well_formed()`'s three-tier fallback (400 tries →
one seeded fallback attempt → 9,600 more tries → logged last-resort) preserves determinism at every
tier (same seed always walks the same salt sequence) and only abandons the well-formed/uniqueness
guarantee at the documented, logged, last-resort tier — matches its own comment about the run #5
fix. `register_for()`'s vote-weighted tie-break (`GENRE_WEIGHT=3` vs `FEATURE_WEIGHT=2`, "two
agreeing features can outvote the source, one cannot") is arithmetically correct against the stated
intent. `name_worlds()` only disambiguates when a carried name has ≥2 occurrences (`if len(items) <
2: continue`), and `taken` is shared across all carried-name groups so cross-name uniqueness (a
coined "Earth" name and a coined "Moon" name can never collide) is enforced globally, not just
within one endonym group. The `[:4]`/`[:9]` slices in `main()`'s console printout are display-only;
`silence.write_json(OUT, named, ...)` writes the complete, untruncated dict. No bugs found.

---

## Cross-cutting notes

- Only `overwatch.py`, `handbuilt.py` (via `reference.py`), and `onomast.py`/`hosts.py` in this
  batch touch shared state on disk. `handbuilt.py` and `onomast.py` both use the correct
  atomic-write contract (`silence.replace_retry` / `silence.write_json`). `hosts.py`'s `add()` does
  not — it's the one write-safety violation found in this batch (see above).
- No subprocess spawns in any of the seven assigned files (all pure-Python/local-file modules);
  the `CREATE_NO_WINDOW` lens item doesn't apply here. `overwatch.py` calls into `allsweep.py`
  and `estate.py` for structural checks, both of which do spawn subprocesses; `allsweep.py`'s
  spawns are correctly guarded with `creationflags=_NO_WIN` (`allsweep.py:50,109,134,298,360`).
