# SWEEP 37 — BATCH 06 AUDIT

**Agent:** sweep37-batch06 · **Date:** 2026-08-28 · **Scope:** 8 modules, 4,004 lines

**Modules read IN FULL, every line:**

| module | lines | read in full |
|---|---:|---|
| `src/foreman.py` | 1,603 | yes (two reads: 1–1063, 1064–1603) |
| `src/silence.py` | 605 | yes |
| `src/onomast.py` | 490 | yes |
| `src/axis_correlation.py` | 384 | yes |
| `src/navtree.py` | 311 | yes |
| `src/coverage.py` | 272 | yes |
| `src/resonance.py` | 220 | yes |
| `src/repass_bands.py` | 119 | yes |

No source file was edited. `foreman.py` and `navtree.py` were imported and exercised
function-by-function; neither was run as a program. No process was started, stopped or killed.
`prose_enabled` and `step4_enabled` were not touched. All demonstrations ran offline against
stubs and scratch directories in the session scratchpad, except two read-only measurements
against `data/NAVTREE.json` and one read-only run of `python src/silence.py` (both explicitly
safe).

**Coverage recorded:** yes — `sweep_plan.record('run37', [...8 modules...], batch=6)` returned
all eight stamped `run37`.

---

## SUMMARY

| severity | count |
|---|---:|
| MAJOR | 5 |
| MINOR | 6 |
| **filed this batch** | **11 orders** |

Order ids: `6e1c72cddfeb`, `1e86b06e7463`, `f194d8444d12`, `99b1ae2c580c`, `881ff7f49438`,
`2583671339d2`, `e5001f0b0153`, `87795c671285`, `89fc2eaf23f1`, `9803b72711b3`, `2cbb690f65a4`.

Not re-filed, as instructed: `bd673ceaaf31` (resonance's dead callers), `b57e23204f66`
(`axis_correlation.rho()`'s fail-open default), `foreman.reprove_pool`'s fixed temp name (already
filed; its six siblings are new and are filed under `99b1ae2c580c`).

---

## MAJOR

### 1. `resonance.hodge_decompose` reports η = 0.0 for exact ladders — `6e1c72cddfeb`
**`src/resonance.py:119`** (the iteration), `:139` (the η).

The loop is plain Jacobi on the graph Laplacian. Jacobi's iteration matrix `D⁻¹A` has an
eigenvalue of −1 on any **bipartite** component, so θ oscillates with period 2 for ever and never
converges there. The gauge-fix at `:126` subtracts only the constant mode, not the alternating
one. The fixed 600-sweep budget then samples whichever phase parity 600 lands on.

Demonstrated offline (`b06_resonance.py`, `b06_hodge2.py`):

| input | η returned | truth |
|---|---:|---:|
| STAR — `a` beats `b`, `c`, `d` (one entity beating three; a pure ladder) | **0.0** | 1.0 |
| BIPARTITE 4×4 — 4 heroes each beat 4 villains by 1.0 (θ=+0.5/−0.5 reproduces the flow exactly) | **0.0** | 1.0 |
| PATH `a>b>c>d` | **0.8889** | 1.0 |
| PATH `a>b>c` | 1.0 | 1.0 |
| transitive K3 (odd cycle) | 1.0 | 1.0 |

`theta['h1']` over the first eight sweeps of the 4×4 case: `[1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0,
0.0]`. At 599 sweeps η=0.8, at 600 η=0.0, at 601 η=0.8. **No iteration budget reaches the right
answer**, because the sequence does not converge.

Two documented claims are false as a result, and one actively misdirects the next reader:

* `resonance.py:59` — "The arithmetic below is correct and has been correct for weeks."
* `resonance.py:96-98` — "If `eta` ever looks under-converged on a well-connected graph, that
  budget — not the arithmetic — is the thing to revisit."

The run #33 sweep renamed the method from "Gauss-Seidel" to "Jacobi" to match the code. The
correction should have gone the other way: Gauss-Seidel converges on this system.

Why it matters even with zero callers: η is "THE MEASURE OF COEXISTENT CONTRADICTION" and feeds
`custodes.convene()`'s Threnody curl-veto. The error runs in the direction that says the
omniverse is *maximally* non-transitive, and `no_evidence` comes back **False** — so the result
is shaped exactly like a confident measurement. This is a separate defect from `bd673ceaaf31`,
and it means the module must not be wired as-is.

Confidence: **high** (arithmetic, reproduced five ways).

### 2. `silence`'s "raise" token can never match a re-raise — `1e86b06e7463`
**`src/silence.py:145`** (`_handlers`) and **`:562`** (`instrument`).

Both tests are `any(t in body for t in (...))` over `"".join(ast.dump(stmt) for stmt in
node.body)`. `ast.dump` spells a raise statement `Raise(...)` — capital R — and the substring test
is case-sensitive, so `"raise" in "Raise()"` is `False`.

```
ast.dump(`raise`)                 -> 'Raise()'                       'raise' in it: False
ast.dump(`raise ValueError('x')`) -> 'Raise(exc=Call(func=Name(...'   'raise' in it: False
ast.dump(`raise exc from e`)      -> 'Raise(exc=Name(id='exc'...'     'raise' in it: False
```

This is a **check that cannot fire, inside the module built to find checks that cannot fire** —
the third such fault in this one function (run #33 fixed `node.name in body`; the ASK-THE-BODY
fix preceded it). It contradicts `silence.py:147-149`'s own stated rule: *"A handler that
re-raises, logs, or carries the exception into its own return value is observed."* Re-raising is
the most observed shape possible and is classified SILENT. Driven through the real `_handlers`, a
handler whose body is a bare `raise` returns `silent=True`; a `raise RuntimeError(...) from e`
returns observed only *by accident*, via the unrelated `uses_exc` clause.

Second, smaller divergence in the same pair of lists: `instrument`'s tokens include `"note"` and
`_handlers`'s do not, so a handler calling a bare `note("...")` is SILENT to `audit()` and
observed to `instrument()` — the siblings disagreeing again, opposite in direction to the
divergence already documented at `silence.py:551-560`.

Measured tree-wide this run: `python src/silence.py` reports **721 handlers, 161 SILENT**. Of
those 161, **6** are misclassifications from these two token faults —

* dead `raise` token (4): `binding_health.py:138`, `gpu_lane.py:498`, `hostcheck.py:163`,
  `silence.py:412`
* missing `note` token (2): `silence.py:360`, `silence.py:365` — which are `replace_retry`'s own
  two handlers, both of which demonstrably record.

The direction is false-positive, not fail-open, so nothing is being hidden. But the module's
headline number is wrong, `--instrument` would inject a redundant `note()` ahead of every bare
re-raise in the tree, and any ratchet counting silent handlers is counting six that record fine.

Confidence: **high** (reproduced against the live `_handlers` and the live tree).

### 3. `foreman.restart_ollama`'s 30-minute rate limit fails open — `f194d8444d12`
**`src/foreman.py:924`.**

`src/foreman.py:921-925` reads `state/OLLAMA_RESTARTS.json` inside a bare
`except Exception: st = {"count": 0, "last": 0}` — no `silence.note`, no message. Line 926 then
evaluates `time.time() - st.get("last", 0) < 1800`, which with `last=0` is False, and the remedy
proceeds to `Stop-Process -Name ollama -Force`.

Verified against the real guard, nothing killed:

| stamp state | verdict |
|---|---|
| healthy, written 2 min ago | REFUSED (rate-limited) — correct |
| torn JSON `{"count": 7, "last": 17` | **PROCEEDS → would kill ollama** |
| truncated to 0 bytes | **PROCEEDS → would kill ollama** |

`python src/silence.py` independently lists `foreman.py:924` among the 161 silent handlers.

This is the **other half of a fault already fixed in this same function**. The comment at
`foreman.py:948-951` names the hazard exactly — *"A denied rename loses the stamp, so the next
round reads no recent restart and is free to kill the daemon again — the guard failing open,
silently."* Run #19 hardened the **write** half (`silence.note` at `:953`) and left the **read**
half untouched. A torn or empty stamp reaches the identical end state, one exit up.

Second consequence: the fallback also resets `count` to 0, so the `(automated restart #N)` figure
— the only signal distinguishing a one-off wedge from a restart loop — resets to 1 each time the
stamp cannot be read. The docstring's promise that "a deeper fault escalates to the owner instead
of being restart-looped into invisibility" depends on both halves.

Confidence: **high** (reproduced).

### 4. Seven hand-rolled FIXED `.tmp` names in a process allowed to run twice — `99b1ae2c580c`
**`src/foreman.py:281`** and six siblings.

| line | target |
|---|---|
| 166 | `data/POOL_PROOF.json.tmp` — *already filed separately (reprove_pool)* |
| 271 | `state/failures_archive.json.tmp` |
| **281** | **`state/failures.json.tmp`** |
| 945 | `state/OLLAMA_RESTARTS.json.tmp` |
| 1319 | `data/OVERWATCH.json.tmp` |
| 1404 | `FOR_OWNER.md.tmp` |
| 1525 | `data/FOREMAN.json.tmp` |

**Two foremen are allowed by design**, which turns this from theory into a live race.
`codewatch.claim_singleton("foreman")` sits inside `if a.loop:` at `foreman.py:1570-1571`, and
the comment above it is explicit: *"ONLY IN LOOP MODE … A one-shot is not a second daemon; it is
a person doing one thing deliberately."* `overnight.STANDING` runs `foreman.py --go --patch
--loop 30` continuously, so any hand-run `foreman.py --go` is a legitimate second writer of all
seven paths.

The failure mode is already documented in this tree, on one of these exact files.
`src/health.py:198-210` records it verbatim for `state/failures.json`: *"both open
failures.json.tmp for writing; the second truncates the first, and whichever renames second lands
a half-written file over the target … failures.json.corrupt held a valid 102-byte document
followed by 38 bytes of a longer, older one — two writers, not one truncated write."* `health.py`
was migrated to `silence.write_json` in run36 for that reason. `foreman.py`, which writes the same
file at line 281, was not — and `foreman.py:237`'s own comment calls it "the highest-traffic
shared file in the project".

`silence.write_json` exists to make this unavailable to get wrong; confirmed live, it produced
`state/failures.json.11156.0.tmp`. All seven foreman sites already check `replace_retry`'s
verdict correctly — only the temp *name* is wrong.

Confidence: **high** on the shape and the two-writer permission; the corruption itself is
inferred from `health.py`'s recorded incident on the same file rather than re-reproduced here.

### 5. The model lane may patch the proving layer — `881ff7f49438`
**`src/foreman.py:95`** (DENYLIST) and **`:1135-1190`** (`_checks_pass`).

`DENYLIST = {foreman, silence, health, allsweep, estate, standards, verify_math}`. Its own comment
at `:93-94` states the rule: *"Each is either the thing that would have to be working to detect a
bad patch, or the thing doing the patching."* Not on the list: **`drill.py`, `escalation.py`,
`codewatch.py`, `liveness.py`, `overnight.py`** — respectively the PROVEN property of Hard Rule
−1, the plant-wide interlock foreman's own `main()` refuses to start without, the rc=17 stale-code
interlock, the check-that-cannot-fail detector, and the supervisor.

And the gate does not cover for the omission. `_checks_pass` runs exactly three things: `import
<module>`, `verify_math.py`, and `allsweep.py --quick`. Verified against `src/allsweep.py:427-520`:
`--quick` runs only the IMPORT and LINT tiers — VERIFY is behind `if not a.quick:` at
`allsweep.py:479` and ESTATE behind the same test at `:498`. Further verified: **`drill` appears
nowhere in `allsweep.py`** and is not in `VERIFIERS` (`allsweep.py:102-118`), so even a full
allsweep never runs it. After a model patch to `drill.py`, not one net is fired before the patch
is kept.

Partial mitigation, recorded so the remedy is not overstated: `verify_math.py` makes ~30
source-level assertions about `drill.py` and `escalation.py` (`:4930`, `:4938`, `:4866`, `:5574`).
Those catch a deletion; they would not catch a weakened comparison inside an individual net.

Confidence: **high on the facts, medium on whether it is a defect.** The gate is accurately
described in foreman's module docstring (`:41-51` lists exactly these three checks), so this may
be a deliberate scope choice. Filed because the DENYLIST comment states a rule the DENYLIST
membership does not satisfy. Note before adding drill to `_checks_pass`: `verify_math.py:5504`
records a standing rule that `verify_math.py` and `drill.py` are not safe to run from an agent
context, and `drill.py` historically wrote trial `prose_enabled` values into the live config
(`verify_math.py:4845-4847`). Adding drill to DENYLIST needs no ruling; running it in the gate
does.

---

## MINOR

### 6. `silence.write_json` overrides a caller's compact-output request — `2583671339d2`
`src/silence.py:404` does `dump_kw.setdefault("indent", 1)`, which defeats a caller's
`separators=(",", ":")`. Verified live: `write_json(t, {'a':{'b':1,'c':[1,2]}},
separators=(',',':'))` produced `{\n "a":{\n  "b":1,\n  "c":[\n   1,\n   2\n  ]\n }\n}`.

One caller affected, confirmed by grepping every `write_json` call site in `src/`:
**`src/navtree.py:297`**, for `data/NAVTREE.json`. Measured against the live file: **411 KB
compact, 589 KB at indent=1 — 1.43×**. The file on disk today is compact, i.e. it predates
navtree's migration to `write_json` (`navtree.py:285-287`), so the inflation has not landed yet
and arrives on the next successful `navtree.py --write`. NAVTREE.json is what `build_terminal`,
`reference` and `sweep` resolve addresses through. Nothing is lost or corrupted; the cost is size.

### 7. A live world is flagged `retired` when its shelf shrinks — `e5001f0b0153`
`src/onomast.py:441-443` builds `merged` as every prior record whose cid is `not in out`, stamped
`retired: True`. `out` holds only cids in `naming`, and `naming` (`:393`) is restricted to cids in
a collision group of size ≥ 2. So a world still present in `resolved`, whose shelf has merely
shrunk to one, is filed under the same flag as a world that has vanished.

Reproduced against a scratch onomasticon:

```
run1 (two Earths):        cid_a -> ('Torutharkok', retired=False)   cid_b -> ('Oriamora', False)
run2 (cid_b removed):     cid_a -> ('Torutharkok', retired=True )   cid_b -> ('Oriamora', True )
  cid_a still in resolved: True     onomast.is_retired(m2['cid_a']): True
```

Consequences are reporting, not data loss: `main()`'s counter at `:468` over-reports
"designations retired, never reissued", and `is_retired()`'s own docstring at `:351` defines the
flag as "issued and withdrawn", so a consumer filtering on it loses a designation still in use and
falls back to the bare endonym — the exact ambiguity this module removes. `navtree` is **not**
harmed: `navtree.py:70-72` builds `by_endonym` from all of `ono.values()` without filtering.

Verified healthy and must survive the fix: the **name reservation works**. The retired record
stays in `prior`, the cid is absent from `naming`, `taken` is seeded with it (`:408-415`), and a
third run cannot reissue Torutharkok — order `9309a040f208`'s whole point.

### 8. Three drifted line-number citations in `navtree` — `87795c671285`

| site | cites | handler actually at | drift | guards |
|---|---:|---:|---:|---|
| `navtree.py:67` | 65 | 66 | 1 | `ONOMASTICON.json` |
| `navtree.py:121` | 118 | 120 | 2 | `GROUNDINGS.json` |
| `navtree.py:127` | 123 | 126 | 3 | `GENRES.json` |

All three point at *different* relative positions — one at the `json.load`, one at the `with
open`, one at the bare `try:` — which is what a stale auto-generated citation looks like. They are
the shape `silence.instrument` writes (`silence.note("{base}:{node.lineno}")`, `silence.py:577`),
inserted mechanically against an earlier layout. The house idiom everywhere else in this batch is
to cite by symbol (`foreman.py:clear_learned_caps`, `coverage.py:so-save`,
`axis_correlation.py:load-matrix`, `onomast.py:coin-exhausted`).

Not cosmetic: `foreman.triage_swallowed`'s docstring (`foreman.py:234`) states the contract these
keys serve — *"the class names the module and the line"*. The three handlers guard three different
files, so telling them apart is the whole value of the key.

### 9. Five report truncations, four of them unannounced — `89fc2eaf23f1`

1. **`resonance.py:194`** — `if len(examples) < 5` caps the `examples` list in a **returned dict**,
   not a print. Verified: 20 vectors → 40 incomparable pairs → 5 examples, no marker. The
   `incomparable` count travels alongside so the information is recoverable.
2. **`repass_bands.py:101-102`** — heading reads *"SURVIVORS — every one of these is an act upon an
   object"* over `kept_entries[:14]`. "Every one of these" over a truncated list is Hard Rule 0's
   exact mislabelling. (The DEMOTED list at `:105-109` is honest: it says "a sample of".)
3. **`onomast.py:470`** — `[:4]` on the carried-name list with no "... and N more", while the inner
   world list at `:476-477` *does* print one. Same function, two disciplines.
4. **`axis_correlation.py:359`** — `ranked[:a.top]`, default 15, no count of what was not shown
   (`measured_pairs` is printed two lines later, so the total is visible).
5. **`coverage.py:243`** — `--show-best`, default 10, **already correct**: announced as "showing 10
   of N; N−10 more not shown", and the sibling WORST COVERED list defaults to everything.
   `coverage.report` is the model the other four should follow. Only nit: `--show-best`'s help says
   "omit via a very large number", which is not `--show`'s honest "omit to print all of them".

### 10. Three latent shapes verified as *not currently firing* — `9803b72711b3`
Filed so they are on the record without being reported as live faults.

* **`foreman._restartable` (`:344`)** authorises a kill using the loose `base in frag or frag in "
  ".join(args)` — the two-loose-substrings class `foreman.py:409-417` documents as fixed for
  `restart_reader`. Its sibling `_restart_horizon` (`:384`) uses the strict `c.startswith(frag)`.
  Both are called by `kill_stalled_job` in the same breath (`:514`, `:541`), so they can disagree:
  kill it, then print that nothing restarts it. **Driven against the real `overnight.STANDING` and
  `lognames.OWNER`: all six managed fragments agree, 0 disagreements today**, because no STANDING
  basename is a substring of a differently-invoked fragment. It goes live the moment a second
  invocation of a STANDING script enters `lognames.OWNER`.
* **`foreman.run_catalogue_gap` (`:798`)** reports an *unmeasured* completeness audit in the words
  of a fully-catalogued library. Verified: with `COMPLETENESS.json == []` (the exact state
  `foreman.py:860-863` records the file having been in), `_catalogue_batch()` returns `batch=[]`,
  `whole=0`, and a person reads "the completeness audit says no source is short". **Mitigated**:
  the remedy returns `did=False` so `round_once` does not break, and `run_completeness_audit` is
  `always` (`:902`), so the re-measurement runs on the same round. Only the message is untrue.
* **`resonance.hodge_decompose` (`:122`)** — `if not nbrs[n]` is structurally unreachable. `nodes`
  is `{n for e in edges for n in e}` (`:100`) and `:114-116` populates `nbrs` for both ends of
  every edge key, so every member of `nodes` has at least one neighbour. Verified across three edge
  sets. Harmless dead defence, but it is `liveness.py`'s exact shape, in a module about safeties
  that are not in effect.

### 11. `coverage._so_load`'s exemption is narrower than its handler — `2cbb690f65a4`
`src/coverage.py:71-72` is `except Exception:` carrying `_ = "silence-exempt: no cache yet is the
normal first state"`. "No cache yet" is `FileNotFoundError`; the handler also swallows a
`JSONDecodeError` from a corrupt cache and a `PermissionError` from a held file, with no trace.

Cost is performance, not correctness — but `coverage.py:58-61` says what the rebuild costs
("deserializing on the order of the whole 874MB corpus per run"), and `coverage.py` is on
`refresh_coverage`'s AUTO path with a 600s timeout (`foreman.py:324`), so a permanently unreadable
memo could quietly convert that remedy into a timeout. The exemption marker is also why nothing
else catches it: `silence.audit()`'s token list contains "silence", so the marker string makes the
handler read as observed.

---

## RECORDED HEALTHY

Verified this run, either by reading against the claim or by exercising the function.

**`silence.py`** — the run-37 changes named in my brief are present and correct.
`replace_retry` (`:331-372`) catches **every** `OSError`, not only `PermissionError`, with a
distinct `replace-failed:` tag, and deliberately does not retry the non-transient class; the
reasoning in the docstring matches the code. `write_json` (`:382-428`) removes its temp on a
DENIED replace as well as on a dump failure, and its temp name carries pid **and** thread ident —
confirmed live as `state/failures.json.11156.0.tmp`. `_discard_tmp` (`:431-443`) is total by
design and correctly so. `replace_if_unchanged` (`:287-328`) keeps ABSENT and UNREADABLE apart via
the private `UNREADABLE` sentinel compared by identity (`:252`, `:305`), refuses a swap over an
unreadable target, and — the part that was wrong before — its **reason now matches its verdict**
on a denied rename (`:324-327`). `digest_of`/`_digest_or_unreadable` maintain the two-valued public
contract while the compare-and-swap gets the three-valued one. `note()` (`:446-478`) arms the
atexit flush once and flushes every 25 records, so a long job's ledger reaches disk while it can
still be stopped. `_ensure_import` anchors on the **first contiguous run** of top-level imports,
which is the correct anchor and the docstring explains why. The export-copy marker check (`:70-74`)
and the eaten-escape check (`:76-78`) both fire at import.

**`foreman.py`** — `_checks_pass` reads verify_math's number by regex rather than substring
(`:1152-1157`) and gates allsweep on the **exit code** rather than a console token (`:1179`), with
the message honestly disclaiming the missing pre-patch baseline. `lines_changed` (`:1097-1110`)
measures changed lines via difflib opcodes, not net length. `regex_touched` (`:1113-1132`) refuses
any patch that alters a metacharacter-bearing literal, and `_literals` (`:1068-1089`) tolerates
only `SyntaxError`, recording anything else. `attempt_patch`'s revert path (`:1281-1299`) reports
honestly when the restore itself fails, naming the backup and the file left holding the patch.
`_function_source` honours a qualifier when the file has one (`:1040-1058`), so two same-named
methods cannot be confused. `kill_stalled_job`'s never-kill-what-you-cannot-restart rule is in
effect (`:514-516`) and escalates SPARED jobs at SUPERVISOR (`:529-536`). `kill_duplicate_jobs`
carries `None` rather than inventing a timestamp for an unreadable CreationDate and skips the job
(`:592`, `:597-600`), and never targets the supervision chain (`:581-583`). `_catalogue_batch`
rotates by last-dispatched-first over a whole universe and prints every deferred, off-roll and
unnameable source **by name** (`:803-814`) — a rate, not a cap, and visibly so. `owner_queue`
prints **every** blocked URL (`:1394-1395`). `round_once` iterates every ranked finding with no
`[:3]` (`:1503-1504`) and survives a raising remedy in both the per-remedy and the whole-round
handlers (`:1451-1455`, `:1581-1589`). The `always` marker correctly stops a successful repair from
suppressing its own re-measurement (`:1472-1485`). `main()`'s escalation import fails **closed**
with a SystemExit naming Hard Rule −1 (`:1539-1551`), and `codewatch.exit_if_stale` is in the loop
(`:1598`). `_restartable` fails closed on an unreadable roster (`:346-350`). `clear_learned_caps`
returns a *different sentence* for an unreadable database than for a healthy zero (`:142-148`).
`adopt_hosts` and `recatalogue_models` both refuse to read a "0 adopted" / a nonzero exit as
success (`:191-194`, `:313-317`). `triage_swallowed` archives before clearing and gates both
writes plus the outer handler (`:278-298`).

**`axis_correlation.py`** — `write()` gates `silence.write_json`'s verdict and returns `None` on a
denial (`:257-260`), and `main()` turns that into a non-zero exit with an explicit "the matrix on
disk is still the PREVIOUS run's" message (`:371-379`). `_no_matrix` fires on **both** the `rho()`
and the `widening()` branches through three channels, deduplicated per site rather than per lookup
(`:106-134`). `_pearson` refuses below `MIN_N` and refuses a constant column (`:196-204`).
`_scores_of` is pure, handles both on-disk shapes, and treats a row with no scores as absent rather
than zero (`:137-158`). `observations()` reports which SOURCES it could not read (`:161-192`), and
`measure()` carries that through to the written document. `main()`'s `mean_r` guard handles `None`
without a TypeError (`:367`).

**`navtree.py`** — both writes are gated and both print an honest denial naming the consequence
(`:273-282` for the audit record, `:297-302` for the tree), and `--write` refuses on a non-empty
audit (`:304-306`). `sources_under` uses the strict-descendant form on **both** arms (`:153`).
Both hash-order tie-breaks (`register_for` at `:168`, the grounding pick at `:180`) are explicit and
repeatable. `audit()` skips a missing child rather than raising on it, so it can report the very
condition it exists to catch (`:216-225`). World lists are uncapped (`:99`).

**`onomast.py`** — `coin_well_formed`'s fallback no longer abandons both invariants: it widens the
same deterministic walk to 10,000 candidates and records loudly when genuinely exhausted
(`:244-265`). `well_formed`'s five constraints are all mechanical and each is justified by a named
ugly output. The `taken` seeding correctly excludes cids about to be renamed, preserving
reproducibility (`:405-415`). `main()` gates the write and says so on a denial (`:480-483`).

**`coverage.py`** — `state_of`'s strict precedence CITED > READ > NO PAGE > NOT ATTEMPTED holds as
written (`:116-130`); NOT ATTEMPTED is a genuine fourth state and NO PAGE is reachable.
`_state_of_file`'s memo is keyed by path **and** name (`:146`), closing the M23 collision one layer
up, and `cachekey.owns` is consulted before a file is believed (`:158`). `_so_save` advances
`dirty` only when the write landed (`:90-91`). `report()` guards its division (`:204`) and prints
the hostless list in full (`:220`). `main()` returns 1 on a denied headline write (`:262-266`).

**`repass_bands.py`** — gates on `PL.write_record`'s verdict and prints WRITE DENIED per source
(`:84-87`). `PL.records()` returns a list (`pipeline.py:459-471`), so `len(recs)` at `:98` is safe.
The module has no exception handling at all, which here is correct: every failure is loud.

**`resonance.py`** — the empty-edge-set and all-zero-flow cases both return `eta: None` with
`no_evidence: True` rather than sharing an answer with a perfect ladder (`:102-110`, `:136-143`) —
order `40b61d3a8c68`'s fix is in effect and is the right shape. `incomparability_rate` correctly
splits UNMEASURED (no shared axis, excluded from the rate) from TIED (decided, not incomparable)
from genuinely incomparable (`:179-199`). The module docstring's "WHAT IS ACTUALLY WIRED" section
(`:40-65`) is accurate about its own dead callers.

---

## METHOD NOTES

Every finding above was reproduced offline before filing. Scratch scripts:
`b06_foreman_probe.py` (the ollama rate limit, the empty completeness audit, the singleton claim),
`b06_restartable.py` (the `_restartable` / `_restart_horizon` comparison against the live
STANDING set), `b06_resonance.py` and `b06_hodge2.py` (the Hodge decomposition on five graph
shapes at three iteration budgets), `v2.py` / `v3_count.py` (the silence token analysis and the
tree-wide misclassification count), `v1.py` (the onomast retirement reproduction). All in the
session scratchpad; none wrote into the project.

Two candidate findings were **discarded on verification**, recorded so the next sweep does not
re-chase them:

* `repass_bands.py` calling `len(recs)` on `PL.records()` — checked; `records()` returns a list,
  not a generator. Not a fault.
* `foreman._restartable` disagreeing with `_restart_horizon` in production — driven against the
  live roster; 0 disagreements today. Filed as latent, not live.
