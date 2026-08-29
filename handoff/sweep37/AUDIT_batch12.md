# SWEEP 37 — BATCH 12 AUDIT

**Modules read IN FULL (3,960 lines, every line):**
`src/assay.py` (1,148) · `src/health.py` (784) · `src/catalogue_web.py` (526) ·
`src/liveness.py` (412) · `src/autostart.py` (347) · `src/runguard.py` (303) ·
`src/render.py` (252) · `src/audit.py` (188).

**Ran (safe only):** `python src/liveness.py`, `python src/health.py --preflight`,
`python src/runguard.py` (status, no flags). Did NOT run `autostart.py`, `catalogue_web.py`
or `assay.py` as programs. Did NOT claim, beat or release the run guard — it is held by
`maintenance-2026-08-28c`, heartbeat 0.6 min old at the time of reading. No source file edited.
No process started, stopped or killed. No model calls.

Every finding below was demonstrated against the live source or the live corpus. Offline probes
were written to scratch and are reproduced inline.

---

## MAJOR

### M1 — `health._flush_ledger` / `_flush_samples`: a read-modify-write on the highest-traffic shared file, with no compare-and-swap. Counts are silently lost.
`src/health.py:150` (`_flush_ledger`), `src/health.py:218` (`_flush_samples`).
**Confidence: HIGH — demonstrated.**

Both functions do: read the file, merge our snapshot into it, write the whole thing back through
`silence.write_json`. `write_json` is ATOMIC (no torn file, pid+thread temp name) but it is not a
COMPARE-AND-SWAP: it does not check that the target still holds what the writer read. Between the
read at `health.py:155` and the write at `health.py:210` another process's flush lands and is
overwritten whole.

The module's own comment at `health.py:184` states the exposure and then addresses only the other
half of it: *"state/failures.json is the highest-traffic shared file in the project — the
dashboard polls it, standards reads it, and EVERY process read-modify-writes it through
health.flush()."* The run36 hardening fixed the shared-`.tmp` collision. Staleness was never
addressed, and `silence.replace_if_unchanged` — the compare-and-swap this codebase grew for
exactly this shape (m42) and which `runguard._land_claim` uses — is not called from `health.py`
at all.

Demonstrated with `LEDGER_PATH` re-pointed at a scratch directory (nothing in `state/` touched);
a competitor flush was injected into the window:

```
on disk at start : {'silent:foo': 10}
competitor landed : {'silent:bar': 7, 'silent:foo': 10}
on disk at end   : {'silent:foo': 15}
expected if no update were lost: {'silent:bar': 7, 'silent:foo': 15}
silent:bar present? False -- the competitor's 7 failures were LOST
```

The loss is doubly silent: `_flush_ledger` then settles `LEDGER` (subtracts `taken`) because the
write *did* land — it just landed over somebody else's. Nothing anywhere records that a merge was
clobbered.

**Why it matters.** This is the failure ledger. The module's thesis is that the recorder must not
become an instance of the defect it exists to expose; under concurrency it is one. It also
supplies the root cause for open order **7c6ef6cb9334** (`FAILURES_LEDGER_MAY_HAVE_EATEN_AN_ATEXIT_FLUSH`),
which named this hazard as *suspected* and *unchased* — it is now reproduced, and the remedy is
named: read + digest, merge, `replace_if_unchanged`, and on refusal re-read and re-merge rather
than settle `LEDGER`.

Filed: **`d770b1896635`**.

### M2 — `liveness` has no MODULE-level DEAD pass, and never judges a class at all. Six modules and one class are wholly invisible to it today.
`src/liveness.py:142` (`_defs`), `src/liveness.py:169` (`scan`).
**Confidence: HIGH — measured.**

The batch brief asks the sharper question of this module: what shapes of unfailable check can it
NOT see. Two, measured on the live tree:

1. **A whole module nothing imports.** `DEAD` is per-symbol, and a function is credited as used by
   `used_local[name]` — a bare-name Load anywhere in *its own module*. Every function in a dead
   module is referenced by its siblings, so a module that no other module imports and no job
   roster names reports **zero** findings, which is exactly what a clean live module reports.
   Measured by AST over `src/` (imports, from-imports, and every string constant equal to a module
   name or `<name>.py`, so a dispatch-table or roster entry counts as a reference):

   **10 modules are never imported or named by any other module in `src/`:**
   `chord_field`, `descending_ladder`, `halo`, `handbuilt`, `module_index`, `pantheon`, `render`,
   `scale_theories`, `wh40k`, `zfighters`.

   Two are already known (`render` — order 707fefc17465, OWNER; `scale_theories` — SWEEP34_FINDING).
   The other eight are not. Six of them — **`halo`, `handbuilt`, `module_index`, `pantheon`,
   `wh40k`, `zfighters`** — appear NOWHERE in `python src/liveness.py`'s output: not one of their
   functions is listed dead, because they are all reachable from each other. `handbuilt` has zero
   mentions anywhere in `src/` outside its own file.

2. **A class.** `_defs` yields `FunctionDef`/`AsyncFunctionDef` and recurses into `ClassDef`, but
   never yields the ClassDef itself, so a class nothing instantiates is not a DEAD candidate — and
   its methods are credited as used through `scoped`, because they call each other on `self`.
   Measured: **one class in the tree is never named anywhere in `src/`** —
   `escalation.py:64 Refused`, `"An OPERATOR- or SUPERVISOR-level stop: this unit or this source,
   not the library."` Never raised, never caught, never imported. Its sibling `SystemHalted` is
   raised at `escalation.py:433` and caught at `verify_math.py:4955`; `prose_gate.py` defines and
   raises its own `ProseRefused` instead. The two rungs of Hard Rule -1's chain that stop a unit or
   a source have a declared exception type with no raiser — a safety in a file rather than in
   effect, invisible to the detector whose subject that is. (Reported here, not filed against
   `escalation.py`, which belongs to another batch this run.)

**A blind spot I checked and found EMPTY, recorded so the next run does not re-measure it:**
a function whose only in-module reference is its own recursive call would be credited as used.
**Zero instances** in the tree today. Cheap to close now, as with the match/case and short-circuit
widenings measured at zero today.

**Why it matters, and the coupling.** `drill.LIVENESS_CEILING` is 41 and `liveness.scan()` returns
34, so there is headroom — but the ceiling ratchets whatever this reports, and what it reports is a
floor at module and class granularity. (Note: open order 6c479972e838 states the ceiling "sits at
38 with ZERO headroom"; that is stale — it is 41 against 34 today.) Order 6c479972e838 covers a
DIFFERENT narrowing (receiver-aware attribute resolution); this is the module/class granularity gap.

Filed: **`209391b4f990`**.

### M3 — `catalogue_web.save_roll` is the last of five writers of `SWEEP_ROLL.json` still on a fixed, shared temp name.
`src/catalogue_web.py:122` — `tmp = ROLL + ".tmp"`.
**Confidence: HIGH — verified by reading all five writers.**

`SWEEP_ROLL.json` has five writers. Four land through `silence.write_json`, whose temp name carries
pid and thread:

| writer | temp name |
|---|---|
| `roll.py:127` | `silence.write_json` — pid+thread |
| `resync_roll.py:115` | `silence.write_json` — pid+thread |
| `catalogue_aurora.py:271` | `silence.write_json` — pid+thread |
| `catalogue_codex.py:260` | `silence.write_json` — pid+thread |
| **`catalogue_web.py:122`** | **fixed `SWEEP_ROLL.json.tmp`, shared by every process** |

The irony is documented in `silence.write_json`'s own docstring: it names
`catalogue_web.save_roll()` as the site that already *had* the atomic version while its siblings did
not — and the migration that carried the siblings onto `write_json` passed the exemplar by, leaving
it on the one convention `write_json` was written to make unavailable. Two processes writing the
roll open the same `SWEEP_ROLL.json.tmp`; the second truncates the first, and whichever renames
second lands a partial roll over a finished one. This is the identical hazard fixed in
`runguard._land` (run #33, `PermissionError` fired 99 times in production), `health._flush_ledger`
and `pipeline.py` (order e080a5f83b3c).

`save_roll` is called under `_wlock` so the three worker threads inside one run are serialised —
the collision is between PROCESSES, which is precisely the case the four siblings were migrated for.

**Second, related exposure in the same function, reported but not separately filed:** `main()` loads
the whole roll once at `catalogue_web.py:405` and `_one` writes the WHOLE object back after each
source. On a large wiki that snapshot is hours old (`catalogue_web.py:251` records DC's `Persons`
class alone taking ~3.8 minutes to rank one category of 33,614 titles), so any change another
writer makes to `SWEEP_ROLL.json` in that window is overwritten wholesale. `silence.replace_if_unchanged`
exists for exactly this and its docstring cites `WIKI_HOSTS.json` being lost this way. None of the
five roll writers uses it, so the correct fix spans more than this batch; it is noted here rather
than filed piecemeal.

Filed: **`0924f1b5af2f`**.

### M4 — `autostart.watch()` never checks whether its own source has changed, and the drill net that would have caught that is hardcoded to three files.
`src/autostart.py:236` (`watch`) and `src/drill.py:4136` (`daemons_actually_check_their_own_source`).
**Confidence: HIGH — verified by grep over every call site.**

Hard Rule -1's fourth property is IN EFFECT: *"a Python process does not re-read its own source."*
The established idiom is `codewatch.claim_singleton(who)` + `codewatch.stamp(who)` in `main`, and
`codewatch.exit_if_stale(who)` inside the loop. Every call site in the tree:

```
src/foreman.py:1571,1572,1598
src/overwatch.py:849,850,864
src/publish.py:1012,1013,1049
```

Three files. `autostart.watch()` is a bare `while True:` at `autostart.py:262` with `time.sleep(180)`
and no staleness check — and it is the LONGEST-LIVED process in the kit. It is started by the
Startup `.vbs` at logon and, as `_twin_watchdog`'s own docstring says, *"nothing restarts the
`.vbs`"*. `autostart.py` imports `codewatch` already, but only for `twins()`.

So every fix to this file — including the pending open order 8c354f6c9780 on `_twin_watchdog`'s
fail-open, and any change to `MAX_STARTS_PER_HOUR` or the tri-state sensor — does not take effect
until the next logon, however green the drill is.

The reason nobody noticed is in `drill.py:4136`: the net is named *"every standing daemon checks
whether its own source has changed"* and it iterates a hardcoded literal
`("publish.py", "foreman.py", "overwatch.py")`. That is a UNIVERSAL claim graded against a
hand-kept subset — the same shape as open order `DRILL_NET_EXISTENTIAL_NOT_UNIVERSAL`, and the
same shape `overnight.STANDING`'s own comment was written to end (*"this roster used to live inside
main() while THREE other places carried their own partial copy of it"*). The real roster is
`overnight.ALL_JOBS` = `autostart.py`, `overnight.py`, `dashboard.py`, `publish.py`, `foreman.py`,
`overwatch.py`, `pipeline.py`, `read.py`, `feats.py --roll`. Of the five in `STANDING`, **`dashboard`
and `pipeline` also have no `exit_if_stale`**, and neither does `overnight.py` itself. The net
passes green over four unguarded long-lived jobs.

Filed: **`bee9d16f4174`** (scoped to `autostart.watch`, naming the net's hardcoded triple as the
reason it went unseen; the `dashboard`/`pipeline`/`overnight` limbs are noted for whichever batch
holds those files).

---

## MINOR

### m1 — `health.check_caches` samples `files[:200]` in arbitrary glob order. A cap, and its stated justification no longer applies.
`src/health.py:467`.
**Confidence: HIGH — measured on the live corpus.**

```python
for fp in files[:200]:
    if os.path.getsize(fp) < EMPTY_BYTES: empty += 1
n = min(len(files), 200)
if empty == n: ...
```

`glob.glob` order is the filesystem's, not a ranking, so this is a prefix of an unordered list
deciding on the corpus's behalf — HARD RULE 0's shape exactly. It is visible in this run's own
preflight output: `feats/www_dandwiki_com (200, source excluded from the roll)` for a directory the
module's own docstring says holds 805 entries.

The comment above it justifies 200 by PARSE cost (*"parsing 200 records for each of 147 hosts meant
reading gigabytes of page text"*) — but the check was changed to `os.path.getsize`, a stat, and the
cost argument went with it. Measured: a capped AND an uncapped pass over **all 256,869 json files**
in `data/feats` + `data/readfeats` together took **19.77 s**, i.e. roughly 10 s for the uncapped
half.

**89 host directories hold more than 200 files** (dc 55,565; marvel 34,239; finalfantasy 26,679;
en_wikipedia 6,392; …). **Measured verdict disagreement between the capped and the uncapped pass
today: 0.** So this is latent, not a live wrong answer — reported at MINOR with the measurement in
both directions.

Filed: **`a6764f7d3d3e`**.

### m2 — `assay.assay` divides by `wsum` with no guard, three lines above the `denom` guard that was added for the identical exposure; and the decimal is clamped at the ceiling but not at the floor.
`src/assay.py:842-843` and `src/assay.py:877-884`.
**Confidence: HIGH — both demonstrated.**

`assay.py:864` carries a long note defending `denom = sum(...) or 1.0`, and its worked example is
`weights={"ruin": 1.0, "celerity": -1.0}` — *"`weights=` is a public per-call override whose VALUES
are unconstrained."* Score BOTH of those axes instead of one and control never reaches that guard:

```
assay("M3", {"ruin": 5.0, "celerity": 5.0}, worksheet="w",
      weights={"ruin": 1.0, "celerity": -1.0})   -> ZeroDivisionError
assay("M3", {"ruin": 5.0}, worksheet="w", weights={"ruin": 0.0})  -> ZeroDivisionError
```

Both die at `wsum` (`assay.py:843`), which has no `or 1.0` and no other guard.

Separately, the ceiling is clamped and the floor is not. `assay.py:869` reasons at length about
`M10.100` being *"a broken ruler: an instrument whose top reading overflows its own notation"*, and
clamps `_dec >= 1.0`. Nothing clamps `_dec < 0`:

```
assay("M3", {"ruin": 0.0, "celerity": 9.0}, worksheet="w",
      weights={"ruin": 1.0, "celerity": -0.5})
  -> moth_number '𝔄 M3.-90 ± 0.53'   decimal -0.9   promotion_due False   at_ladder_ceiling False
```

Reachability today: no caller passes negative or zero-sum weights — `custodes.CUSTODES`'
`axis_emphasis` tables are all positive multipliers ≥ 1.0 (verified for all ten Custodes). So this
is latent, hence MINOR. What makes it worth filing is the asymmetry: Layer 1 (`_check_scores`)
validates the caller's SCORES and refuses anything off the axis scale, while the `weights=` table
that multiplies them is validated by nothing.

Filed: **`8b74d2b4f569`**.

### m3 — `assay.instrument()` has no Layer-1 validation, and its hard cap turns a data error into a plausible top reading.
`src/assay.py:941`.
**Confidence: HIGH — demonstrated.**

`_check_scores` is called from `assay()` only. `instrument()` is a public entry that takes
`axis_scores` directly and publishes faculty values 1-30:

```
assay("M3", {"ruin": 99.0}, worksheet="w")                    -> AssayIntegrityError (correct)
instrument("M4", {"ruin": 99.0, "celerity": -40.0, ...})["faculties"]
  -> {'Strength': 30, 'Dexterity': -30, 'Constitution': 24, ...}
```

`99.0` becomes a Strength of exactly 30 — the maximum the Instrument can print, indistinguishable
from a legitimately maxed reading. That is the outcome `_check_scores`'s own docstring refuses:
*"A clamp would turn a data error into a plausible reading."* And `-40.0` becomes `-30`, outside the
Instrument's own declared 1-30 range, because `min(30, ...)` at `assay.py:987` has no lower bound.

Callers today are `anchors.py:186` (hand-written module constants, all in range) and `verify_math`,
so this is latent — MINOR.

Filed: **`5f99aa19c059`**.

### m4 — `catalogue_web` derives each entry's `type` with `rstrip("s")`, which strips every trailing `s`.
`src/catalogue_web.py:351` — `"type": cats[0].rstrip("s") if cats else canon.split(" (")[0].rstrip("s")`.
**Confidence: HIGH — demonstrated.**

```
Goddesses -> Goddesse    Bosses -> Bosse      Classes -> Classe
Princess  -> Prince      Colossus -> Colossu  Characters -> Character
```

`str.rstrip(chars)` removes a SET of characters, not a suffix. A wiki category ending in `ss` or
`sses` — and `Princess`, `Goddesses`, `Bosses`, `Colossus`, `Classes` are ordinary Fandom category
names — writes a mangled `type` into every entry harvested from it. The value is stored in the
record, not merely printed. `catalogue_composite` avoids this only by hardcoding `"type": "Deity"`.

Filed: **`0a5019b2527e`**.

---

## VERIFIED HEALTHY — checked, and found correct

Recorded so the next run does not re-derive them.

**`health.py`**
- The preflight stamp gating (`health.py:738-753`) is present and correct: `landed` is captured,
  the `except` and the `False` return are BOTH handled, `silence.note("health.py:preflight-stamp-denied")`
  puts a machine-readable trace in the ledger, and the stderr line names the consequence. The
  residual — `workorders.PREFLIGHT_MAX_AGE` is 6 h, so a denied stamp can leave an up-to-6-h-old
  green stamp grading the battery — is stated in the source itself and is bounded. Not filed.
- Lock ordering is sound. `_LOCK` is never held while `_FLUSH_LOCK` is taken; `silence.note`
  (`silence.py:476`) calls `health.flush()` outside every lock; the `_FLUSHING` thread-local
  re-entry guard is correct for the `replace_retry -> note -> flush` cycle it names. No deadlock.
- `_flush_samples`' identity-matched settle (`id(x)` over the snapshot) is correct: `taken_s` copies
  the list but not the sample dicts, so identities survive.
- `_flush_ledger` settles `LEDGER` only on a landed write, and subtracts rather than clears. Correct.
- `summary()` returns `{"ledger:unreadable": 1}` rather than `{}` on a torn ledger — correct, and it
  is the distinction `main()` depends on.
- `check_caches`' quarantine and roll-exclusion exemptions both go through the shared helpers
  (`cachekey.host_dir`, `roll.OUT_OF_SCOPE`) rather than re-spelling them, and both fail loud
  (empty exemption set) when their source cannot be read. Correct.
- `check_state` and `reopen_stranded` both ask `pipeline.entry_settled` — one copy of the rule.
- Ran clean this shift: 5/5 checks ok, backlog 18,470 entries printed as info, not as a fault.

**`runguard.py`**
- Digest-before-read verified in all three of `claim`, `beat`, `release`; the ordering argument in
  the comments is correct in each direction, and the CAS is on the write in all three.
- A JSON-CORRUPT guard does not wedge the pass: `read()` fails on the JSON but
  `_digest_or_unreadable` opens `rb` and returns a real digest, so `replace_if_unchanged` matches
  and the claim lands — which is what `read()`'s docstring promises. Only a BYTE-unreadable guard
  refuses, and that is transient. The two "unreadable"s are correctly different.
- `holder_is_live` treats a missing, non-numeric or stale heartbeat and `done: true` alike, as
  documented. `_land_claim`'s temp name carries pid and thread and its failure path removes it.
- Open order 372d4a8c8d46 (the residual digest→rename window) still stands and is unchanged; I did
  not re-file it.
- Read only. The guard was NOT claimed, beaten or released.

**`assay.py`**
- `_check_constants`' last two branches are False at import by construction — measured:
  `max(vals) = SIGMA_UNKNOWN = SIGMA_MAX = 3.7444`. They are NOT dead: `drill.py:1089` and
  `verify_math.py:5175` re-call the function after rebinding, which is the edit they police. The
  docstring's defence (against run #34 order 02277646a783) is correct and should stand.
- `calibration_report()` re-derives the charter's published numbers through the live code rather
  than asserting a stored constant, and it holds: `{'interval': 0.12, 'want_interval': 0.12,
  'decimal': 0.52, 'want_decimal': 0.52, 'holds': True, 'sigma': 1.7973, 'band_lo': 1.725,
  'band_hi': 1.870, 'margin': 0.997}`. The sweep uses the per-call `sigma=` override and touches no
  shared table.
- `_interval` uses the caller's `weights=` table for both the composite and the bar (the 2026-08-24
  fix) and applies rho over EVERY applicable pair, not only scored ones.
- `_rho_doc`'s fallback announces on stderr, permanently on `RHO_FALLBACK_REASON`, and on every
  assay's `correlation_source`. `_rho` delegates to `axis_correlation.rho` rather than
  reimplementing it.
- **One observation, verified and NOT filed:** `interval_from_hands`' returned
  `covers_all_signatures` is True by construction — the `while any(abs(v-centre) > interval)` loop
  immediately above it guarantees the `all(abs(v-centre) <= interval)` it then computes. Measured:
  **0 Falses over 20,000 random three-Hand readings across every attestation grade plus an unknown
  one.** It is not filed because it IS a mutation target (verify_math L1089/L1098 flip the loop and
  the assertion, and both checks then fail) and because `verify_math.py:5209` already recomputes the
  property independently from `signatures` and `centre`. Recorded so a future consumer does not
  read the field as a runtime verification: in unmutated code it cannot be False.

**`liveness.py`** (beyond M2)
- The three tightenings noted in the brief are present and correct: `_defs` recurses into
  `ClassDef` with a dotted label; `_self_attrs`/`_classes`/`scoped` resolve `self.foo` per class and
  its ancestors AND descendants rather than globally; PHANTOM walks `ast.match_case` guards and bare
  `ast.Expr(BoolOp)` statements, taking the line from the test where `match_case` has no `lineno`.
- The `used` set correctly separates the three scopes (`used`, `used_local[name]`, `reachable`), and
  bare names are Load-only, which is the `coverage._p()` fix.
- PHANTOM's `defined` set seeds from `import builtins` rather than `dir(__builtins__)`, and adds the
  interpreter-supplied dunders and all three `Match*` capture forms.
- `_parse` carries the REASON, and an unparsed module is a finding rather than a silent `continue`.
- `_modules()` scans only the top level of `src/` and skips any file starting with `_`; there are no
  `_`-prefixed `.py` files today, and `src/deprecated/` is correctly out of scope. Not a live gap.
- `python src/liveness.py` this shift: **0 tautology, 0 phantom, 34 dead, 0 unparsed.**
  `drill.LIVENESS_CEILING` = 41, so 7 of headroom.

**`audit.py`**
- Live: `allsweep.py:109` runs it as `("catalogue backscan", ["audit.py"])`.
- `_JUNK`'s per-alternative anchoring is correct — the `$`-anchored furniture words cannot fire as
  prefixes, and only `Category:`, `List of `, `Index of ` and `Characters` stay prefixes, which is
  the documented intent.
- Invariants read from outside the enforcing code, over EVERY entry, and `main()` returns 1 when
  anything fails. The `v[:4]` in the report is a print truncation that prints the full count and
  `... and N more` beside it — not a cap on a stored field.
- The seeded sample is reproducible and both `rng.sample` calls are `min()`-guarded against a short
  pool.

**`autostart.py`** (beyond M4)
- `supervisor_alive()`'s tri-state is honoured at both consumers: `watch()` declines to act on
  `None`, and `main()`'s install path tests `alive is False`, not `not alive`.
- The start budget is correct: the window is pruned before the count, and both log lines are
  rate-limited so a persistent condition writes one line an hour.
- `_twin_watchdog` now retries `TWIN_TRIES` times and WRITES the fail-open into `autostart.log`,
  and it delegates process resolution to `codewatch.twins` rather than substring-matching a
  filename. Open order 8c354f6c9780 describes the pre-retry state and reads partly stale as a
  result; the *design* question it raises (fail-open vs fail-closed) is still the owner's.
- `_vbs_body()`'s `Chr(34)` quoting produces
  `"<python>" -u "<...>\autostart.py" --watch` — verified by hand-expanding the concatenation.
- `_NO_WIN` is named once and used at both call sites, per the no-console-windows rule.
- `start_supervisor` closes its log handles in a `finally`, so a long-lived watchdog does not leak
  2N handles.
- `--status` reads `ON.ALL_JOBS`, the single roster, not a hand-kept subset.

**`catalogue_web.py`** (beyond M3 and m4)
- The three items named in the brief are present and correct: `slug` is `catalogue_aurora.slug`
  re-bound to the same object (no 60-char cap anywhere in the path), `record_path` prefers the file
  that already exists, and `save_roll()` returns its verdict with `_one` checking it and printing
  `ROLL WRITE DENIED` without counting the source failed.
- `write_record_catalogue`'s verdict IS checked before `entry_count`/`status` are set — the failure
  mode described at `catalogue_web.py:487-493` is closed.
- `MAX_PER_SOURCE` is `None`, the tripwire at `catalogue_web.py:313` would refuse if anything set
  it, `rank_by_size(top=None)` and `category_members(limit=None)` rank without truncating, and the
  proportional trim is gone. The `--limit` flag is an explicit operator request, not a silent cap.
- `no_text` and `failed_cats` are counted, named in the run log AND written into the record's own
  `provenance` with the correct epistemic framing (upper bound on absence, not a claim of absence).
- The two progress lambdas both use the default-arg freeze, and `_short` is correctly rebound per
  fetch unit.
- **Observation, not filed:** `MAX_PER_CATEGORY` and `CATEGORY_SCAN_DEPTH` are both `None` and are
  read by NOTHING — not inside this module, not in any other module in `src/`. Their comments say
  they are "kept only as a name other code may import"; nothing imports them. Harmless (nothing can
  truncate by them), but they carry no tripwire of the kind `MAX_PER_SOURCE` has, so the asymmetry
  is worth knowing about if either is ever revived.

**`render.py`** — read in full. The unreachability is order **707fefc17465** at OWNER rung and is
NOT re-filed. Two further latent things inside it, reported for whoever handles that order:
- `children_of` (`render.py:181`) filters on `for t in prefix if t in coord`. A coord that omits the
  tier key filters NOTHING and returns the children of every pool, silently, as data. `view()`
  passes `coord or {}`, so `view("universe")` with no coord reaches this.
- `view("system", galaxy=None, star=None)` (`render.py:197`) builds a URL containing the literal
  string `None` rather than refusing. Same for `planet`/`burg` with `map_seed=None`.
- `containment_svg`'s `[:26]` on a child name and `children_of`'s `[:24]` are SVG label truncations
  with the full count carried in `weight`; `DRAWN`/`FETCHED` are a partition of `TIER_ORDER`, not
  caps. No Hard Rule 0 violation in this module.

---

## Coverage

Recorded by this batch:
`sweep_plan.record('run37', ['assay.py','health.py','catalogue_web.py','liveness.py',
'autostart.py','runguard.py','render.py','audit.py'], batch=12)` — see the run below.
