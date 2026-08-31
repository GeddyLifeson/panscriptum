# run39 — batch 11 audit

Modules owned (taken from `sweep_plan.batches(16)[10]['modules']`, not from any typed list), each
read IN FULL, no sampling:

| module | lines |
|---|---:|
| `src/overnight.py` | 1527 |
| `src/allsweep.py` | 850 |
| `src/rosetta.py` | 635 |
| `src/weave.py` | 546 |
| `src/canon_backup.py` | 418 |
| `src/grounding.py` | 334 |
| `src/context_budget.py` | 296 |
| `src/cachekey.py` | 190 |
| `src/lognames.py` | 52 |

Read-only audit. No source file was edited. Every finding below was checked against the current
source (and, where it names another module, against that module's current source) before being
written down.

---

## 1. MAJOR — `allsweep.py:526` asks a MENTION question where this tree has a purpose-built RUN test

`reconcile()`'s process roster does:

```python
live = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]   # :517
import overnight as _ON                                                      # :524
for job in _ON.ALL_JOBS:
    n = sum(1 for ln in live if job in ln)                                   # :526
```

`job in ln` is a substring test against the whole command line. `overnight._cmd_is_running`
(`overnight.py:281-325`) exists precisely because that construction is wrong, and its docstring
names this file as the case that proved it:

> "THE SECOND ARM USED TO BE `fragment in cmd`, AND THAT IS A MENTION TEST, NOT A RUN TEST.
> `allsweep` lints the tree with `pyflakes src/codewatch.py src/publish.py src/foreman.py
> src/overwatch.py`, which names four daemons in one command line, so for the ~120 seconds that
> linter runs every one of them reads as UP."

Verified: `allsweep.py:628-631` is itself exactly such a command — `python -m pyflakes` with the
absolute path of **every** module in `src/` on one command line. Any concurrently-running lint
(another allsweep, a foreman `--patch` check, `mutate`) puts `dashboard.py`, `publish.py`,
`foreman.py`, `overwatch.py`, `pipeline.py` and `read.py` on one process's command line at once,
and this loop then reports `MORE THAN ONE INSTANCE RUNNING` for six jobs simultaneously.

The same test also lacks `overnight._in_this_tree` (`overnight.py:256-278`), so a `mutate.py`
sandbox copy answers for the live job — the confusion that once HALTED the library
(`codewatch.twins()`, run #34).

Why it is not merely cosmetic: RECONCILE rows are ungraded by design, but `overwatch.py` reads
them and treats an ALL-CAPS `finding` as a fault (recorded at `allsweep.py:577`), and
`MORE THAN ONE INSTANCE RUNNING` is all-caps. A false duplicate-supervisor alarm reaches a person.

**Remedy.** Replace the substring test with the pure function already imported in the same block:
`n = sum(1 for ln in live if _ON._cmd_is_running(job, ln))`. `_cmd_is_running` is pure, takes the
same two strings, and already handles the `feats.py --roll` two-word fragment. Filed as
`ALLSWEEP_PROCESS_CHECK_IS_A_MENTION_TEST`.

Note the earlier sighting: `handoff/sweep29/AUDIT_batch07.md:176-179` raised only the
job-name-*collision* hypothesis at this line ("none currently are... HYPOTHESIS only"). The
mention-vs-run defect is a different and live one, and `_cmd_is_running` did not exist when that
was written.

## 2. MINOR — `allsweep.py:424` is the surviving hand-spelled twin of `cachekey.host_dir()`

```python
live = {_re.sub(r"[^A-Za-z0-9]+", "_", h)[:40] for h in hosts.values() if h}
```

`cachekey.py`'s own header (lines 84-94) rules: "ONE HELPER, NOT FOUR SPELLINGS... If a sixth site
is ever found, add it to this list rather than to the drift." `cachekey.host_dir()`
(`cachekey.py:115-117`) is `_SANITISE.sub("_", host or "")[:HOST_CAP]` with `HOST_CAP = 40` — this
line is byte-for-byte that formula, re-spelled.

Verified as a KNOWN OPEN item, not a new one: `handoff/run35/AUDIT_batch5.md:176-188` records
order `5159320dd758` fixing the `hostcheck.py` twin and explicitly leaving this one
("`allsweep.py` was **not** touched: it is not in this run's owned-files list, so a follow-up task
was spawned instead (`task_46e8858a`)"). That follow-up has not landed; the line is still here,
now at `:424` rather than the `:242` that audit cites.

Also verified: `verify_math.py:7520-7531` pins the fix for `hostcheck.py` only
(`'cachekey.host_dir(mined)' in src_txt`), so nothing in the battery watches this site.

The values agree today, so nothing is currently mis-computed. The exposure is that a change to
`HOST_CAP` or `_SANITISE` silently makes every host directory look stale to the
`cache directories no source points to` row. **Remedy:** `import cachekey` and use
`cachekey.host_dir(h)`; extend the `verify_math` pin to this file.

## 3. MINOR — `overnight.py:963-972` pins the one blocking preflight condition by POSITION, not identity

```python
import health as _health
_control_label = _health.CHECKS[0][0]
...
blocking = ("FAIL  " + _control_label) in out
```

The comment above it (947-962) is right about what it fixed — two hand-typed cross-module string
literals — but the replacement reaches into `health.CHECKS` by **index**. Verified:
`health.py:827-833` currently has `("control characters in source", check_control_chars)` first,
so the value is correct today. Reorder that list (add a check above it, sort it) and
`_control_label` silently becomes `"context budget"`: the halt gate then blocks on a different
check and stops blocking on the corrupted-source one, with no error anywhere.

The guard three lines below cannot catch that. `if _control_label not in out:` tests whatever
label was fetched, and *that* label will be in the output, because it is a real check that
health prints. So the "the halt gate had nothing to read this cycle" line stays silent through
the exact failure it is written for.

**Remedy:** select by identity, not by position — either look the row up by name
(`next(l for l, _ in _health.CHECKS if "control character" in l)`, refusing if it is absent) or,
better, have `health.py` export a named `CONTROL_CHARS_LABEL` constant and read that, so the
identity is a declaration rather than an ordering accident. Filed as
`OVERNIGHT_BLOCKING_LABEL_PINNED_BY_INDEX`.

(This is a *new* finding created by the fix. The previous state is described at
`handoff/sweep38/AUDIT_batch11.md:56-64`, which audited the two-literal version; that version is
gone.)

## 4. MINOR — `overnight.py:1503-1507` reads an unreadable halt ledger as "not halted", and records nothing

```python
try:
    import escalation as _ESC
    _halted, _rec = _ESC.status()
except Exception:
    _halted, _rec = False, None
```

Two separate problems, both verified against the file:

1. **It is the only handler in this module that leaves no mark.** Every other swallow here calls
   `silence.note` — `:78`, `:151`, `:154`, `:450`, `:490`, `:903`, `:910`, `:915`, `:933`,
   `:1000`, `:1028`, `:1042`, `:1118`, `:1240`, `:1276`, `:1300`. `_keep_warm`'s own comment
   (`:1268-1275`) calls out being "the one handler in this file that recorded nothing at all
   (found run #19)" and fixes it. This is a second one, at a strictly more important gate.
2. **It fails in the direction the surrounding comment says must never be taken.** The comment at
   `:1489-1502` records the self-inflicted outage: the supervisor read jobs-exiting-on-purpose as
   jobs-crashing, exited, and nothing came back even after the halt was cleared. This handler
   reproduces exactly that: an unreadable escalation module means `_halted = False`, the
   `if _halted:` wait branch is skipped, and the supervisor `break`s out of the loop with
   "That is not an idle library, it is a broken one."

The same file already knows the right direction. `_manager_stopped` (`:489-491`) answers
`True, "escalation unreadable; refusing to start on an unknown answer"` on the identical failure,
and `main()` at `:1142-1154` and `:1313-1320` raises `SystemExit` rather than assume clear.

**Remedy:** `silence.note("overnight.py:idle-halt-status-unreadable")` in the handler, and treat
an unreadable answer as "wait and look again" (the `_halted` branch) rather than as "not halted",
matching `_manager_stopped`'s fail-closed rule. Filed as
`OVERNIGHT_IDLE_HALT_CHECK_SWALLOWS_UNREADABLE_ESCALATION`.

## 5. MINOR — `overnight.py:539-541` conflates "the authoritative probe went blind" with "already running"

`run()` builds a distinct status for a blind probe at `:514-517`, with a comment saying why:
"Distinct status so the cycle's summary line does not claim the stage was found already up."

Three lines later, `_guarded_popen` makes the *authoritative* check under the spawn lock and
returns `None` for **two** different reasons — blind probe (`:385-388`) and already-running
(`:389-391`) — and `run()` maps both to one string:

```python
p = _guarded_popen(name, args, fh, banner=_banner)
if p is None:
    return "already-running"
```

So in the window between the unlocked pre-check and the locked one (the window the lock exists
for), a stage skipped because the process table could not be read is reported to the cycle, and
into `state/overnight.log`, as a stage that was found already up. Both statuses land in `busy`
(`:1476`) so the idle counter behaves the same; what is lost is the diagnosis, in the log a
person reads at 3am. `start()` has the same shape but returns `None` for both, which its callers
treat identically, so no status is misreported there.

**Remedy:** have `_guarded_popen` distinguish its two refusals (a sentinel, or a `(proc, why)`
pair) and let `run()` return `"probe-blind"` for the blind one. Filed as
`OVERNIGHT_GUARDED_POPEN_CONFLATES_BLIND_WITH_RUNNING`.

## 6. MINOR — four stale cross-references to the `shared_sample` family, verified one by one

`cosmology_graph.py:115-119` and `tiers.py:309-313` both cite the sibling sites of the WHOLE-list
ruling by line number. Every citation was checked against the current file:

| citation | claims | what is actually there now | the real line |
|---|---|---|---|
| `weave.py:478` | writes `shared_sample` under the ruling | `resolved, homonyms = resolve(index, groups)` | `weave.py:519` |
| `pipeline.py:1795` | writes `shared_sample` under the ruling | the handoff-write `except` arm's `log(...)` | `pipeline.py:2375` |
| `cosmology_graph.py:86` | the site brought in line in run #26 | `UBIQUITOUS_CUTOFF = 12` | `cosmology_graph.py:116` / `:209` |
| `resonance.py:146` | reads `shared_sample` back | `nbrs[b].append((a, -f))` in the phase loop | `resonance.py:295` |

Confirmed by `grep -n shared_sample src/*.py`: the only writers are `cosmology_graph.py:209`,
`pipeline.py:2375` and `weave.py:519`, and the only reader is `resonance.py:295`.

The content of the claims is still true — all three writers do carry the whole list. Only the
addresses have rotted, which is the same defect `STALE_XREF_FOREMAN` is already open for and
which `weave.py:212-215` fixes in its own `silence.note` label ("Content label, not a line
number... A stale number costs a grep every time someone diagnoses it"). **Remedy:** replace the
four numbers with content labels (`weave.py`'s `shared_sample` write, etc.), which survive the
next edit. Filed as `STALE_XREF_SHARED_SAMPLE`.

## 7. MINOR — `allsweep.py:323` + `:698`: a failed verifier's output is truncated twice, and the discarded half exists nowhere

```python
"tail": [ln for ln in out.strip().splitlines() if ln.strip()][-14:]     # :323
...
for ln in r["tail"]:
    print(f"      {ln[:150]}")                                          # :698
```

The 14-line window is what is *stored* in `data/ALLSWEEP.json`, not merely what is printed — the
rest of a failing verifier's output is discarded in-process and is recoverable from nothing. That
is the shape `reconcile.note`'s own comment (`:348-357`) was written against: "unlike every other
capped list in this file the full set existed nowhere -- not on the console, not in
ALLSWEEP.json."

The 150-character clip at `:698` is the same cut this file removed 35 lines earlier, for reasons
it states itself (`:663-669`): "on this machine the absolute path alone eats most of 100, which
puts the identifier a person needs past the cut." A verifier traceback line is exactly such a
line.

Neither cut announces itself: no "… and N more", no ellipsis. Compare `art['bad'][:25]` at
`:712-716`, which prints "... and N more (full list in ALLSWEEP.json)" and genuinely keeps the
whole list — the shape this file already declares to be the right one.

**Remedy:** keep the whole `out` (or a much larger window) in the stored row, print a head with an
explicit "… and N more lines, full output in ALLSWEEP.json", and drop the per-line `[:150]`.
Filed as `ALLSWEEP_VERIFIER_TAIL_TRUNCATED_TWICE`.

## 8. MINOR — `rosetta.py:480-481` reports a FETCH failure as a SEARCH failure

```python
if errs:
    failed[h] = "%d of %d searches did not come back" % (len(errs), len(SCALE_QUERIES))
```

`errs` is the list `scales_for` fills, and it takes entries from three places, only two of which
are searches:

* `:230` — `"%s: %s (%s)" % (q, ...)`, a search that raised. A search.
* `:233` — `"%s: no response" % q`. A search.
* `:247-248` — `"fetch of %d page(s): %s (%s)"`. **Not** a search: this is the single
  `F.fetch(host, sorted(seen))` call at `:243`, which happens after every search has succeeded.

So a wiki whose thirty-one searches all worked and whose one page fetch was throttled is reported
as "1 of 31 searches did not come back" — a message that sends the reader to the search step and
understates the loss, since a failed fetch costs the host *every* scale it had already found
(`:249` returns `{}`). This is the two-conditions-one-message shape, in the mine's only
per-host explanation of why a wiki came back empty.

**Remedy:** count the two classes separately (the fetch entry is identifiable by its prefix, or
`scales_for` can return them in two lists) and word the line for whichever occurred. Filed as
`ROSETTA_FETCH_FAILURE_REPORTED_AS_SEARCH_FAILURE`.

## 9. MINOR — `weave.py:475-495`: `main()`'s report carries four undisclosed cuts

```python
for g in multi[:12]:
    print(f"   {len(g):>3}  {[x[:26] for x in g[:4]]}{' ...' if len(g) > 4 else ''}")   # :475
...
for v in sorted(resolved.values(), key=...)[:8]:
    print(f"     {v['canonical_name'][:30]:<32}{v['n_attestations']:>3}  "
          f"{[x[:18] for x in v['attestations'][:3]]}")                                 # :487
for k, n in byk.most_common(6):                                                          # :493
    print(f"     {names.get(k, k)[:26]:<28} {n} distinct entities")
```

* `multi[:12]` — no marker. The count is printed on the line above, so a reader *can* subtract;
  `g[:4]` on the same line does carry a `' ...'`, which shows the author's own standard.
* `[:8]` (`:487`) and `most_common(6)` (`:493`) — heads of ranked lists with no count and no
  marker beside them.
* `v['attestations'][:3]` — a mid-value cut of the evidence list, printed next to
  `n_attestations`, which is the untruncated count; the discrepancy is undisclosed.
* `x[:26]`, `x[:18]`, `[:30]`, `[:26]` — mid-name cuts, unmarked.

This is the shape `grounding.py:297-304` was corrected for by owner order e2b3af23cb8a
("`low[:5]` printed the first five in dict order... while the count beside it said 15") and that
`feats._show` already refuses. Display-only — the JSON written at `:510-523` is uncapped, verified.
Filed as `WEAVE_MAIN_REPORT_CAPS`, LOCAL, MINOR.

## 10. MINOR — `canon_backup.verify()` promises "which files changed" and delivers only a count

Docstring (`:297-302`): "What this answers is the narrower and more useful question: is the
archive itself still intact and readable, **and which canonical files have changed** since it was
taken."

What it actually appends:

```python
notes.append("%d canonical files changed since the snapshot" % len(changed))     # :350
if added:
    notes.append("%d canonical files are new since the snapshot" % len(added))   # :352
if gone:
    notes.append("... GONE ...: %s" % ", ".join(sorted(gone)))                   # :357
```

`changed` and `added` are computed and their contents thrown away; only `gone` is named. `main()`
(`:394-395`) prints the notes and nothing else, so the names exist nowhere after the call
returns. The set is bounded by the canonical inventory (~219 files) and this only runs on an
explicit `--verify`, so the volume argument the module rejects for `missing` (`:145-151`) and for
`gone` (`:354-356`) does not apply here either.

**Remedy:** name `changed` and `added` the way `gone` is named, or narrow the docstring's promise
to what is delivered. Filed as `CANON_BACKUP_VERIFY_NAMES_ONLY_THE_GONE`, LOCAL, MINOR.

## 11. INFO — `weave.null_threshold` is dead like its sibling, and is the only one of the pair not annotated as such

`weave.py:161` (`pair_weights`) carries a three-line comment: "SUPERSEDED, NOT CALLED ANYWHERE...
Reported, not deleted, per house doctrine that dead code is not automatically deletable: order
25ec11447b4c / sweep33 batch08 finding 8." Its permutation-null twin `null_threshold`
(`weave.py:275-299`) has no such note.

Verified dead: `grep -rn "null_threshold\b" src/*.py` excluding `null_threshold_surprisal` returns
the definition and nothing else. `pipeline.py:2359` and `tiers.py` both call
`null_threshold_surprisal`.

The dead-code fact itself is long-known (reported in sweeps 22, 25, 26, 27, 28, 30, 31, 34, 38)
and the owner has repeatedly chosen to keep it, so the fault filed here is only the missing
annotation: one of a matched pair carries the "reported dead, not deleted" marker and the other
does not, which is what makes the next reader re-file it. Filed at INFO as
`WEAVE_NULL_THRESHOLD_UNANNOTATED_DEAD`.

## 12. INFO — `cachekey.py:54` is read by nothing; `cachekey.py:144` shadows the module's own import

* `HERE = os.path.dirname(...)` at `:54` is used nowhere in the module (`grep -n HERE
  src/cachekey.py` → one hit, the definition) and by no importer (`grep -rn
  "cachekey.HERE\|CK.HERE\|_CK.HERE" src/*.py` → nothing), across the fifteen modules that import
  `cachekey`.
* `text_digest` does `import hashlib` at `:144` although `hashlib` is imported at module level at
  `:49`. Unlike `silence.write_json`'s local imports, which carry a comment explaining the idiom,
  this one is unexplained and simply shadows.

Neither is a behaviour fault. Filed together at INFO as `CACHEKEY_DEAD_CONSTANT_AND_SHADOWED_IMPORT`.

## 13. INFO — `overnight.py` still clips the substance of three reported findings per line

The module has removed every *list* cap it was carrying (`did[:5]` at `:687-689`, the
`open_f[:top]` at `:720-727`, `ledger_report`'s trailing slice at `:739-748`) — each with a
comment explaining why the cap was wrong. What survives is the per-line character clip on the
value each of those lists exists to carry:

* `:693` — `a.get('result', '')[:70]`, the foreman remedy's own result string.
* `:729` — `f.get('actual', '')[:96]`, the overwatch finding's actual observation.
* `:874` — `ln[:160]` in `tail()`, the failed job's last words.
* `:1005`, `:1047` — `err[-1][:160]`, the last stderr line of a preflight/drill that did not
  complete.

`state/overnight.log` is, by this module's own account (`:600-606`), "the forensic record an
incident gets reconstructed from". The same argument `allsweep.py:663-669` makes about the
100-character clip applies here at 70 and 96. Kept at INFO because these are log lines whose full
value does still exist in the source artifact (`FOREMAN.json`, `OVERWATCH.json`, the job log
itself), which is the difference from finding 7. Filed as `OVERNIGHT_LOG_LINE_CLIPS`.

---

## Recorded, deliberately NOT filed

**`rosetta.check()`'s `ambiguous_assay_names` describes the wrong map on the scoped path.**
`:360-369` builds `a_by`/`collided` from the *global* normalisation on every call, and `:387`
stamps `len(collided)` onto every report row — including rows produced under `by_host` scoping,
where `a_by` is never consulted (`known = a_by if by_host is None else by_host.get(host, {})`,
`:372`) and `main()` is the only production caller and always passes `by_host` (`:599`). Verified
in source. Not filed because `handoff/sweep38/AUDIT_batch04.md:158-164` already recorded it as an
observation with the same reasoning ("No live consumer reads the field"), and re-queueing a
deliberate not-filed is queue churn.

**`rosetta.py`'s CLI caps (`:457`, `:459`, `:567`, `:569`, `:606`, `:613`).** Real, and exactly
the shape of finding 9 — but already open as `ROSETTA_CLI_CAPS` (MINOR, checked against the live
queue this run). Not refiled.

**`rosetta.py --probe` cannot tell a throttled wiki from an empty one** (`:456` calls
`scales_for(a.probe, verbose=True)` with no `errors=` list, so the whole apparatus at `:210-214`
is unused on the one interactive path). Verified still true; already open as
`ROSETTA_PROBE_ERRORS`. Not refiled.

**`overnight.py:1431` — the serial `run("pipeline", ...)` is effectively unreachable.** Verified
still true and the code's own comment (`:1416-1430`) says so and explains why it is left in
pending an owner ruling. Already open as `SWEEP34_FINDING` at `src/overnight.py:842` (the same
line, since renumbered). Not refiled.

## Questions (two defensible readings; recorded, not filed as findings)

**Q1. `rosetta.numeric_rows`'s outlier filter drops rows without counting them.**
`:177-179`: `if len(out) >= 8: out = {k: v for k, v in out.items() if v <= med * 1000}`. The
reasoning in the comment is sound (a parse artefact a thousand times the median would dominate a
rank correlation single-handedly) and this is a *filter*, not a display cut — but nothing anywhere
reports how many rows it removed, whereas `refine()` four hundred lines later carefully returns
`kept, dropped` for its own filter and `main()` prints both. Both readings are defensible: "a
filter is not a truncation" and "a filter whose volume is never reported is how a parser bug
hides". Not filed.

**Q2. `rosetta.py --check` exits 0 when every scale is UNSCORED.** `:624-628` returns 1 only on
`bad` (rho < 0.3). A run in which all eight scales come back `rho: None` prints "That is not
agreement; it is no measurement" (`:615-617`) and exits 0, and `allsweep`'s
`franchise rank agreement` row (`allsweep.py:201`, RC_BROKEN) grades that green — which is the
same total-blindness state the module's own docstring at `:345-352` records having been in for
eleven runs. Against filing: an unscorable scale genuinely is not a disagreement, the rc contract
is documented, and making it exit 1 would make the row red on a legitimately thin corpus. Not
filed; it is a judgement about what the exit code should mean, which is an owner's call.

**Q3. `overnight._proc_lines`'s "empty listing" branch may be unreachable.** `running()` at `:222`
has `if not out: return False`, but `_PROCS["at"]` is stamped only after a non-empty read
(`:156-157`), so a cached `""` always fails the TTL test and re-spawns. The branch therefore looks
dead. It is also a correct fail-safe if the invariant ever changes, and the module's tri-state
comment (`:127-130`) argues the *opposite* reading — that an empty listing is UNKNOWN, not
"nothing running", which is what `_proc_lines` already returns `None` for. Recorded as a
consistency question rather than filed as dead code.

## Read and found sound

Checked and found correct, so a later reader does not have to re-derive them:

* `cachekey.load()` / `write_path()` — the read-verifies-ownership fix is complete: `load` treats
  a parsed-but-foreign document as a MISS (`:173`), `write_path` only disambiguates when the
  natural path is held by a *different* entity (`:240-241`), and `provenance_ok` genuinely returns
  three states with `None` for "nothing was recorded" (`:218-219`).
* `lognames.py` — every constant has at least one live reader (`READ`, `ROLL`, `PIPELINE`,
  `OWNER` many; `SWEEP`, `RECATALOGUE`, `CALIBRATE` one each, verified by grep across `src/`). The
  `SWEEP = "sweep.py"` / `allsweep.py` basename collision the header worries about cannot fire,
  because `_cmd_is_running` compares basenames rather than substrings, and `verify_math.py:6893`
  pins that.
* `context_budget` — `content_budget_chars` can legitimately return ≤ 0 and its one live consumer
  handles it correctly: `manifest_builder.py:370-375` raises `ContextOverflow` rather than
  clamping. The split prose/content ratios are both set *below* their measured values, so the
  refusal keeps its stated safety direction.
* `grounding` — `classify_text(top=None)` really does return the whole field (a `Counter` gets a
  key for every grounding because `scores[name] += 0` creates it), so `confidence`'s denominator
  is the full field and `runners_up` is the full field minus the winner. `A.regress_test`
  (`assay.py:1204`) accepts every keyword each `GROUNDINGS[...]["regress"]` dict supplies.
* `canon_backup` — `members(strict=True)` refuses on any absent declared path (`:121-126`), and
  `snapshot()` never passes `strict=False`; the read-back re-hashes every member from inside the
  zip; `prune()`'s half-removed pair correctly counts as NOT removed; `silence.replace_retry`
  returns only `True`/`False` (verified at `silence.py:445-461`), so `:188`'s `is False` test is
  sound.
* `weave` — `filtered_index` reads the whole description for both gates, `surprisal_pair_weights`
  and `pair_weights` both keep the whole `shared` list, and the three-file write at `:510-541`
  grades each verdict independently and warns about the out-of-step case.
* `allsweep` — `_row_is_fault` fails closed on a keyless row; `run_verifier`'s `rc_means` falls
  back to `RC_BROKEN` for an undeclared row; the LINT tier's `rc not in (0, 1)` predicate really
  does catch an absent pyflakes; `bad` now sums imports + verifier grades + lint + estate files +
  estate findings + the report-not-landed case. `_HALT_REFUSAL` is imported from
  `escalation.HALT_REFUSAL` (`escalation.py:64`), and the import-not-copy change is correct: the
  old row could only compare two references to one constant.
* `overnight` — `name_rc`'s unsigned→signed NTSTATUS fold, `_in_this_tree`'s deliberate fail-open,
  `_guarded_popen`'s banner-under-the-lock, `_manager_stopped`'s both-spellings fail-closed gate,
  `coverage_snapshot`'s rc-**and**-mtime double check, `write_status`'s build-then-`replace_retry`
  with the window disclosed in the heading, and the `busy` / `manager-stopped` / `probe-blind`
  idle accounting.

---

## Orders filed (13)

| severity | code | id | where |
|---|---|---|---|
| MAJOR | `ALLSWEEP_PROCESS_CHECK_IS_A_MENTION_TEST` | 07cb6bdabd36 | allsweep.py:526 |
| MINOR | `ALLSWEEP_HANDSPELLED_HOST_DIR_TWIN` | c499e168fd48 | allsweep.py:424 |
| MINOR | `OVERNIGHT_BLOCKING_LABEL_PINNED_BY_INDEX` | 15150e8442fc | overnight.py:963-978 |
| MINOR | `OVERNIGHT_IDLE_HALT_CHECK_SWALLOWS_UNREADABLE_ESCALATION` | e41c9c2e4839 | overnight.py:1503-1507 |
| MINOR | `OVERNIGHT_GUARDED_POPEN_CONFLATES_BLIND_WITH_RUNNING` | 6a3e4238042d | overnight.py:539-541 |
| MINOR | `STALE_XREF_SHARED_SAMPLE` | ca6bc5a2e148 | cosmology_graph.py:115-119, tiers.py:309-313 |
| MINOR | `ALLSWEEP_VERIFIER_TAIL_TRUNCATED_TWICE` | 2da56d4307ea | allsweep.py:323, :698 |
| MINOR | `ROSETTA_FETCH_FAILURE_REPORTED_AS_SEARCH_FAILURE` | eca7cb1d2d8f | rosetta.py:480-481 |
| MINOR | `WEAVE_MAIN_REPORT_CAPS` | 357e24fa2fa1 | weave.py:475-495 |
| MINOR | `CANON_BACKUP_VERIFY_NAMES_ONLY_THE_GONE` | 323703189931 | canon_backup.py:296-359 |
| INFO | `WEAVE_NULL_THRESHOLD_UNANNOTATED_DEAD` | 905f13a21f0c | weave.py:275-299 |
| INFO | `CACHEKEY_DEAD_CONSTANT_AND_SHADOWED_IMPORT` | 42fa60f85054 | cachekey.py:54, :144 |
| INFO | `OVERNIGHT_LOG_LINE_CLIPS` | fc7d688c1c6a | overnight.py:693,729,874,1005,1047 |

Handler rung: BOTS for the five whose target is on `local_agent.DENYLIST` (`allsweep`,
`overnight`); LOCAL for the eight whose targets are not (`weave`, `rosetta`, `canon_backup`,
`cachekey`, `cosmology_graph`, `tiers`).

`lognames.py`, `context_budget.py` and `grounding.py` produced no order: all three were read in
full and every check, cap and error path in them was found sound or already correctly annotated.

---

## 14. MAJOR — the batch this audit was dispatched with no longer exists (`sweep_plan.batches` reshuffles mid-sweep)

Found while recording coverage, and it affects the whole of run39, not this batch.

`sweep_plan.batches(n)` (`:102-115`) is a pure function of the LIVE line counts of every file in
`src/` (`modules()`, `:69-99`, opens each file and counts). Greedy longest-first bin packing means
a one-line change to ANY module re-packs EVERY bin. Reproduced this run:

* **At dispatch**, `SP.batches(16)[10]['modules']` returned nine modules, 4,848 lines —
  `overnight.py, allsweep.py, rosetta.py, weave.py, canon_backup.py, grounding.py,
  context_budget.py, cachekey.py, lognames.py`. All nine were read in full; this audit is those
  nine.
* **~90 minutes later** the same call returns eight *different* modules — `overnight.py,
  allsweep.py, rosetta.py, liveness.py, withdraw_chapters.py, navtree.py, tells.py, audit.py`.
* Six of the original nine had moved: `weave.py`→12, `grounding.py`→12, `canon_backup.py`→14,
  `context_budget.py`→10, `cachekey.py`→16, `lognames.py`→4. Five modules now labelled "batch 11"
  were never in this agent's brief and were **not** read by it.

The cause is ordinary rather than exceptional. `find src -name '*.py' -newermt '-90 minutes'`
lists eight edited files in that window — `mutate.py` 22:23, `allsweep.py` 22:28,
`escalation.py` 22:28, `verify_math.py` 22:35, `publish.py` 22:37, `local_agent.py` 22:39,
`drill.py` 22:59, `workorders.py` 23:04. The STANDING set runs `foreman.py --go --patch`
(`overnight.py:781-782`, `:1368-1369`), whose model lane edits `src/` unattended by design. A
moving `src/` is the *normal* condition of the tree during a sweep.

Two consequences:

1. **Batch membership is neither stable nor provably disjoint.** Overlapping sets duplicate work;
   a module can fall out of every dispatched brief if the coordinator dispatches at t0 and any
   agent recomputes later.
2. **`check_briefs()` recomputes `batches(n)` at check time** (`:487`), so running it after any
   `src/` edit reports `dropped`/`added` faults against a coordinator whose dispatch was exactly
   right — a net that fires on a correct dispatch, the shape `allsweep.py:458-461` names ("a false
   alarm is as corrosive to an audit as a missed fault"). Its docstring promises the comparison
   "available BEFORE dispatch"; nothing makes it mean the same thing afterwards.

**What still holds, so this is not a completeness failure.** `missing(run)` (`:437-441`) and
`check_briefs`'s `uncovered` (`:508`) both compare the union of ALL shards against the CURRENT
`modules()`, and `covered_by()` unions rather than overwrites — so a module that fell out of every
batch does surface. The proof is intact; the plan's stability, its disjointness and the
pre-dispatch check's post-hoc meaning are not.

**Remedy:** freeze the plan for the life of a run — `batches(n, snapshot=None)` fed a recorded
module/line table, written once to `state/sweep_plan/<run>.json` at dispatch and read by agents
and by `check_briefs` instead of recomputed. Keep `missing()` on the live `modules()` list, which
is what lets a module ADDED mid-run still be reported uncovered; that direction is the fail-safe
one and must not be frozen. Filed as `SWEEP_PLAN_BATCHES_RESHUFFLE_MID_SWEEP` (MAJOR / BOTS, id
`4d44a6363245`).

**Coordinator note.** `SP.record('run39', ...)` for this batch was called with the nine modules
actually read, not with whatever `batches(16)[10]` says at the moment it is next asked. Five
modules — `liveness.py`, `withdraw_chapters.py`, `navtree.py`, `tells.py`, `audit.py` — now carry
the label "batch 11" and have not been audited by this agent; check `SP.missing('run39')` at the
end of the run rather than assuming the numbered briefs partitioned the tree.
