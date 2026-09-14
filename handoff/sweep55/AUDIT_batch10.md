# AUDIT — sweep run55, batch 10

Modules read (every line of each, in order): `publish.py`, `sweep_plan.py`, `scout.py`,
`weave_index.py`, `address.py`, `burgs.py`, `navtree.py`, `cosmology_graph.py`,
`compress_store.py`. Nothing under `src/`, `data/`, `state/` or any ledger was edited.
Nothing from `C:\Users\imarl\panscriptum-export` was executed; the export tree was
inspected read-only once (a `find` for code files under its `handoff/`) to check the
`a66423722e45` claim below. `publish.py` was never run.

The only code executed this shift was a four-line synthetic file in the session scratchpad
(`ub.py`) that reproduces the `import X` inside a function / `UnboundLocalError` semantics
used in Finding 4, and one read-only `json.load` of `data/CHARTER_SPINE_CODES.json` to
count single-token index names. No module in the batch was imported or driven.

---

## The three questions the brief asked

### Order `a66423722e45` — the 28 executable-suffix files under `handoff/`

**It does what it claims, and it is in effect, not merely on file.**

Measured now: `find handoff -type f` over the seventeen suffixes in `publish._CODE_EXT`
returns exactly **28 files**, all `.py` — 18 `handoff/run35/checks_*.py` and
10 `handoff/nets_20260906/*.py`. No `.sh`/`.ps1`/`.bat`/`.js`/anything else exists there, so
the widening under orders `e7e00ffde6c5` / `749597eb95d4` closed a latent hole rather than
changing today's output, exactly as its comment at `src/publish.py:214-233` claims.

The rule is three mechanisms and all three are live:

* `_is_agent_scratch` (`src/publish.py:236-241`) refuses the copy — head of the
  repo-relative path in `CODE_FREE_DIRS`, extension in `_CODE_EXT`. Called inline at
  `src/publish.py:1105`, before `wanted.add(rel)`, so a refused file contributes nothing
  to `wanted`.
* `prune_export` (`src/publish.py:986-1003`) therefore deletes the already-published copy
  on the same cycle. This is the half that "withdraws what is already there".
* `gitignore_lines()` (`src/publish.py:254-273`) derives `handoff/**/*.py` and
  `handoff/*.py` from the same two constants, so `git add -A` cannot re-admit a file that
  reached the export by some other route.

Verified against the export tree: `C:\Users\imarl\panscriptum-export\handoff` holds **zero**
files of any of those suffixes, against 28 in the live tree. The drill net
`drill_agent_scratch_gate` (`src/drill.py:16906-16947`) attacks the predicate from both
directions and names `handoff/nets_20260906/unlocated.py` explicitly, and it asserts the
negative side too (`.md` audits and `.json` queue state still publish, `src/publish.py`
still publishes).

Two things a reader should know that the rule does not say:

* The ten `nets_20260906/*.py` are **staged drill nets already merged into `src/drill.py`**
  (fifteen comment citations there, e.g. `src/drill.py:16831`, `16927`), so refusing to
  publish them loses nothing. They are not load-bearing code that the public repo now lacks.
* The withdrawal only happens while `prune_export` is *allowed* to run. If
  `_why_no_delete_in_export()` fires (missing/unreadable `.is-export-copy`, or `SITE`
  resolving onto the live tree), `prune_export` returns `None`, and already-published
  agent scripts stay in the public repo behind a rule that reads as though it worked. The
  refusal is loud (`src/publish.py:966-971` plus the stdout line at `src/publish.py:1243`),
  so this is disclosed, not silent — recorded here as the standing condition of the claim,
  not as a defect.

### Order `bf316bbb7f89` — `freeze_plan(run, n)` checking `frozen_plan(run)`

**Verified, and the race is real as filed.** `src/sweep_plan.py:284-308`:

```
existing, reason = frozen_plan(run)      # 284  -- a bare os.path.exists + open
if existing is not None: return existing # 285-286
if reason != "absent": return {... frozen: False ...}   # 287-291
table = modules()                        # 292
...
silence.write_json(plan_path(run), rec, indent=1)       # 299  -- unconditional overwrite
```

There is no lock, no `O_EXCL` create, and no read-back. Two callers for the same `run` that
both observe `"absent"` at line 284 both compute a table at line 292 and both write at line
299; `silence.write_json` lands through `replace_retry`, which overwrites unconditionally.
The loser returns its **own** `rec` with `"frozen": True` while a different plan is on disk —
so the batch a coordinator dispatches from can differ from the batch a later
`frozen_plan(run)` hands out, which is the precise failure freezing exists to prevent.
The window is `modules()` (a walk of `src/` plus a line count of ~120 files), which is not
short. Previously filed; not re-filed here, recorded as re-confirmed against source.

Two smaller things on the same function, not part of that order:

* `n` is **silently ignored** when an existing plan is returned (line 285-286). `freeze_plan('run55', 24)`
  against a frozen 16-batch plan returns the 16-batch plan and `main()` then prints
  `# plan for run=run55 is FROZEN`, with no line saying the requested `n` was not honoured.
  Idempotency is right; the silence about the mismatch is the part worth a ruling.
* `check_briefs` reads `frozen["batches"]` (`src/sweep_plan.py:927`) after `frozen_plan`
  has only proven the **key exists**, not that it holds a list of `{"batch","modules"}`
  dicts. A dict whose `batches` is a string or a number raises `TypeError`/`KeyError` out
  of the pre-dispatch check — the "second, smaller mouth" of `9508f9322b4c` one level down.

### Orders `d1709d8e757d` / `2cb442afd901` — what the staleness check currently measures

Not answering the owner question. Reporting the instrument as it stands
(`src/weave_index.py:432-518`):

* **The verdict that raises the work order is a clock and nothing else.**
  `stale = bool(age_hours > STALE_HOURS)` — `src/weave_index.py:506`, `STALE_HOURS = 48.0`
  at line 429. `age_hours` is `(time.time() - os.path.getmtime(data/ENTITY_INDEX.json)) / 3600`.
  No property of the corpus enters this decision. An index rebuilt 47 hours ago against a
  corpus that has since been entirely rewritten is reported **not stale**; an index rebuilt
  49 hours ago against a corpus nothing has touched is reported **stale**.
* **The corpus signal exists, is computed, is reported, and does not raise anything.**
  `behind = bool(newest is not None and newest > idx_mtime)` — line 505, where `newest` is
  the max mtime over `data/records/*.json` from `_records_sig()`. It is binary: "at least
  one record file is newer than the index". The comment block at lines 477-504 records why
  it was deliberately demoted out of the verdict (measured 1 of 216 records newer against a
  23.9h-old index — an alarm that would always sound).
* **The only quantity resembling "how much of the corpus moved" is a count of FILES.**
  `modified_since` (lines 459-466) counts record **files** whose mtime exceeds the index's,
  and `total_records` (line 517) is `len(files)` — the number of `*.json` files in
  `data/records/`, **not** the number of entries. On this corpus that is ~216 files for
  ~200k entries, and one file (`marvel.json`, 27 MB, 30,207 entries) counts as 1. So the
  fraction available to any future ruling is at file granularity, and `build()`'s real
  entry total (`total`, `src/weave_index.py:401`) is never passed to `staleness()`.
* `modified_since` is computed only when `coarse_stale` (`behind or age>48`) and `files` is
  non-empty; otherwise it stays `None`. In the common measured state (`behind=True`,
  `stale=False`) the full per-file `getmtime` pass runs and `escalate_if_stale` then
  returns at `src/weave_index.py:534` without reading it.
* **Nothing but this module calls either function.** `staleness()`'s only caller is
  `escalate_if_stale()`; `escalate_if_stale()`'s only caller is this module's `main()`
  (grepped over `src/*.py`). So the order the check files can only be filed by somebody
  running `weave_index.py` by hand — and because the escalation sits *before* `build()`
  (`src/weave_index.py:576`), a `--write` run refreshes the order's `last_seen` on the very
  invocation that fixes the staleness. (`weave.index_staleness()` in `weave.py` is a
  separate mechanism and is outside this batch; the module docstring's claim that
  "`verify_math` already ANNOUNCES this -- twice a run" traces to `weave.load_index`'s
  `weave.py:index-stale` note, per `src/verify_math.py:1676-1680`, and I could not confirm
  the "twice a run" figure from inside this batch.)

---

## MAJOR

### MAJOR — the credential scanner silently skips a directory it cannot list, and the push proceeds

**Where:** `src/publish.py:578` (`for base, dirs, files in os.walk(root):`), inside
`scan_for_secrets`, reached from `push()` at `src/publish.py:1593`.

**What:** `scan_for_secrets` walks the staged export tree with a bare `os.walk(root)`.
`os.walk`'s default `onerror` is `None`, which means an `OSError` from `scandir` on any
directory is **swallowed and that branch yields nothing** — no exception, no `silence.note`,
no entry in `hits`.

**Why it is wrong:** every file under an unlistable directory is never opened, never
scanned, and contributes no finding, so `leaks` comes back empty and `push()` runs
`git add -A` / `git commit` / `git push` on bytes that nothing examined. This is the exact
property the function's own docstring promises it does not have: *"SIZE IS NOT A REASON TO
SKIP, AND UNREADABLE IS NOT CLEAN. Both used to be a bare `continue` ... a file that
genuinely cannot be read is REFUSED BY NAME as an `UNSCANNABLE` finding rather than
skipped"* (`src/publish.py:536-546`). That repair was applied at **file** granularity —
the `except Exception` at `src/publish.py:657-662` does emit an `UNSCANNABLE` hit, and
`push()`'s filter at line 1593 only drops `SUPPRESSED`, so an unreadable *file* correctly
blocks the push. It was not applied at **directory** granularity, so the same failure class
is fail-closed one level down and fail-open one level up, inside one function. This is the
identical asymmetry `weave_index.py` was corrected for under order `5f1dc97d5216`
(`src/weave_index.py:283-303`: *"The PER-FILE handler eight lines above was hardened for
exactly this failure class and this coarser one was not"*).

The house pattern is already in this file: `sync_tree` walks the live tree as
`os.walk(root, onerror=walk_errors.append)` (`src/publish.py:1099`) and **holds** the whole
subtree when any error arrives, on the stated ground that nothing may be decided on the
word of a failed read. The one walk whose failure is irreversible and outward-facing is the
one that does not ask. Norton locking newly-written objects under this tree is named in
this module's own header as a live, recurring condition, and `sync_tree` has just finished
writing into that tree when `push()` scans it.

**Confidence:** read `scan_for_secrets` end to end and traced the two error paths; confirmed
by reading `push()`'s call site and its `leaks` filter, and by contrast with
`sync_tree`'s `onerror=` two hundred lines below. I did **not** run it (it is on the publish
path). CPython's `os.walk` swallowing `scandir` errors when `onerror is None` is documented
behaviour, not an inference about this code.

### MAJOR — `unknown_claims`'s "NOT SILENT" handler raises `UnboundLocalError` instead of noting

**Where:** `src/sweep_plan.py:771` (`silence.note("sweep_plan.py:shard-unreadable")`), in
the second shard loop of `unknown_claims()`.

**What:** `sweep_plan.py` does not import `silence` at module scope (module imports are
`argparse, glob, hashlib, json, os, sys as _sys, threading, time`). Every other handler in
the file does a guarded `try: import silence / except Exception: pass` before calling it —
including the **first** loop of this same function at `src/sweep_plan.py:747-751`. The
second loop's handler calls `silence.note(...)` bare. Because `import silence` appears
inside the function body (line 748), `silence` is a function-**local** name throughout
`unknown_claims`; if line 748 never executed, line 771 reads an unbound local.

**Why it is wrong:** a shard that is readable in the first loop and unreadable in the second
— a shard mid-`replace_retry` from a concurrent `record()`, exactly the sixteen-agents
topology this module is built for, or one removed between the two passes — raises
`UnboundLocalError` **out of the `except Exception` handler** and out of `unknown_claims`.
The same happens if `import silence` itself fails. The caller is
`main()`'s `--missing` arm (`src/sweep_plan.py:1085`), which is the falsifier half of the
completeness proof: `python src/sweep_plan.py --missing run55` would traceback after
printing "nothing missing", so the run reads as complete and the check that would have
falsified it never ran. The handler's own comment is the indictment: *"NOT SILENT ... a
shard nobody could read would quietly shrink the set of claims being falsified"* —
and the handler written to prevent that is the one that breaks.

**Confidence:** grepped every `silence` reference in the file (48 sites; line 771 is the
only unguarded one, and the only one not preceded by a guaranteed binding in the same
function). Confirmed Python's function-local-import semantics with a four-line synthetic
reproduction in the scratchpad: `True noted` / `False UnboundLocalError: cannot access local
variable 'silence' where it is not associated with a value`. I did not run `unknown_claims`
itself (it reads `state/sweep_shards/`).

---

## MINOR

### MINOR — `scan_for_secrets`'s safety argument names a caller that does not exist

**Where:** `src/publish.py:558`.

**What:** the docstring justifying the `only=` parameter reads *"an argument that can make
it read less is a loaded gun: `write()`/`push()` call it with `only=None` and the drill's
`_the_scanner_reads_files_over_two_megabytes` net ... proves the unnarrowed walk still sees
an oversized file"*.

**Why it is wrong:** `write()` (`src/publish.py:1421-1451`) does not call
`scan_for_secrets` at all — it makes `docs/`, takes a snapshot and lands `state.json`.
`grep -n scan_for_secrets src/*.py` gives exactly two live call sites in this module's own
package: `src/publish.py:1593` (in `push()`) and the drill's. This is the same defect order
`f4ed53f4691b` already fixed on the *next clause of the same sentence* (a net name that had
been renamed); the reader checking the safety argument for a parameter the docstring itself
calls a loaded gun is told to go and look at a caller that isn't there, and could reasonably
conclude a second unnarrowed call site protects them. The named drill net *does* exist
(`src/drill.py:4621`), so only the `write()` half is stale.

**Confidence:** read `write()` in full; grepped all `scan_for_secrets` occurrences in `src/`;
confirmed `_the_scanner_reads_files_over_two_megabytes` at `src/drill.py:4621` and its
registration at `4593`.

### MINOR — `_unpushed`'s comment claims a `[:80]` that is no longer there

**Where:** `src/publish.py:789` ("The origin/main arm's `[:80]` is left alone; it sits on a
path that still returns a count.") against `src/publish.py:756`
(`detail = "no origin/main to compare against (%s)" % str(e)`).

**What:** the second `except` arm's comment asserts that a sibling truncation survives in
the origin/main arm and explains why it was left. Order `ca4f97d6b64d` removed that `[:80]`
— the arm's own comment at `src/publish.py:750-755` says so in the first person.

**Why it is wrong:** finding-type 4, and specifically harmful here: the next reader auditing
truncation in this file is told there is a live unmarked cut at a location that no longer has
one, and the two comments in one function contradict each other about the same expression.

**Confidence:** read both arms and quoted the code between them.

### MINOR — `push()` treats "could not tell whether we are ahead" as "nothing to send" before the push and as `PushHeld` after it

**Where:** `src/publish.py:1634-1644` versus `src/publish.py:1716-1727`.

**What:** on a clean worktree, `ahead, why = _unpushed()`; `if not ahead:` catches both `0`
and `None`, prints an advisory on **stderr** when `ahead is None`, and `return False` —
which `main()` renders as `"no change to push"` with `rc=0`. Forty lines later, after a
successful `git push`, the identical `ahead is None` reading raises
`PushHeld("... Unconfirmed is not landed ...")` with `rc=1`.

**Why it is wrong:** one function answers the same question two opposite ways, and the arm
that fails open is the one a wrapper reads. `PushHeld`'s own class docstring is an argument
that stderr is what a wrapper throws away and that a return value can be mistaken for
success; that argument applies unchanged to line 1644. Concretely: a repo whose `.git` is
locked (`git rev-list` non-zero, not the unborn-branch diagnostic, so `_unpushed` correctly
answers `None` per order `0224d12400d1`) and whose worktree is clean reports
`no change to push`, `rc=0`, on every cycle, while commits may be stranded. The comment at
lines 1636-1641 acknowledges the choice, so this may be deliberate — **filed as a QUESTION,
not as a fix**, per the brief. What is not in doubt is that the two readings of `None` in one
function disagree.

**Confidence:** read `_unpushed` and both `push()` call sites; traced `main()`'s rendering at
`src/publish.py:1907`.

### MINOR — a failed attempts-stamp in `scout.sweep` is noted but never said, and it restores the pinning bug the function was written to remove

**Where:** `src/scout.py:637-639`.

**What:**
```
landed, _ = _mutate(ATTEMPTS, _stamp)
if not landed:
    silence.note("scout.py:attempts-unwritable")
```
No stderr line, nothing on stdout, and the cycle continues.

**Why it is wrong:** the whole ordering fix documented in `sweep()`'s docstring
(`src/scout.py:566-585`) turns on `SCOUT_ATTEMPTS.json` recording that these sources had
their turn. If the stamp does not land, every source in `order` sorts as
never-attempted (`0.0`) again next cycle, so `foreman.scout_hostless`'s 30-second loop
re-scouts the same four sources for ever and everything ranked fifth and below is never
attempted — the exact measured failure ("15 hostless sources, of which 4 could ever be
reached") the ordering was changed to remove. Compare the **read** side twelve lines above
(`src/scout.py:627-631`), which prints a loud stderr paragraph for the same class of event
with the same consequence spelled out. One half of the rotation's persistence says so and
the other does not.

**Confidence:** read `sweep()` end to end; traced `_mutate`'s `landed` contract
(`src/scout.py:139-175`, never raises, returns `(False, why)`); the discarded second member
`_` is the reason string, so the `why` is also dropped.

### MINOR — `scout.verify()` runs `import endpoint` and `EP.html_text` outside its try, so one raise ends the whole cycle

**Where:** `src/scout.py:314` (`import endpoint as EP`) and `src/scout.py:327`
(`text = EP.html_text(body)`), against the `try` that covers only `urlopen` at
`src/scout.py:315-325`.

**What:** the fetch is wrapped and classified into three named failure reasons; the import
and the HTML-to-text step are not. `verify()` is called from `scout()`'s loop
(`src/scout.py:409`) with no handler, and `scout()` is called from `sweep()`'s loop
(`src/scout.py:642`) with no handler.

**Why it is wrong:** this is the same shape order `d57377577891` fixed one screen below, for
`EP.register`, and that order's comment states the cost exactly: *"one raise took down the
WHOLE CYCLE rather than one source: `results` was discarded, so the SCOUT.json write and the
ARCHIVE append never ran ... and the attempt stamps written BEFORE the work still stood, so
every source in the batch ... had spent its rotation slot for nothing."* The fix was applied
to the one `endpoint` call in `scout()` and not to the two in `verify()`, which sit on the
same cycle and carry the same consequence. I could not demonstrate `html_text` raising on
real input, so the weight of this rests on the unguarded `import` and on the structural
argument, not on a reproduction — flagged as such.

**Confidence:** read the call chain `sweep() -> scout() -> verify()` and confirmed no handler
at any level; `foreman.scout_hostless`'s outer `except Exception` is outside this batch and
does not restore the discarded `results`.

### MINOR — `weave_index`'s staleness reports "not behind" when it could not read the corpus at all

**Where:** `src/weave_index.py:455-456`.

**What:** `files, sig = _records_sig()` then `newest = sig[1] if sig else None`.
`_records_sig` returns `sig=None` on purpose whenever any entry was unstattable or the
records directory itself would not list (`src/weave_index.py:270-306`). `staleness()`
collapses that into `newest = None`, which makes `behind = False` (line 505) and drops the
mtime term out of `coarse_stale` (line 458), and the returned dict carries no field saying
the signature was unavailable.

**Why it is wrong:** "the corpus is not ahead of the index" and "I could not find out whether
the corpus is ahead of the index" come back as the same value, in the one function whose
whole subject is whether a derived artefact has fallen behind its source. It is the rule
`_records_sig`'s own two error handlers were rewritten to honour, one call up.
Consequence is bounded today because `stale` is a pure clock (see above) and
`escalate_if_stale` reads only `stale` — but `behind` and `modified_since` are the two
fields the module explicitly publishes *for whoever rules on the fraction question*, and they
will read as "the corpus did not move" for a pass that never managed to look.

**Confidence:** read `_records_sig` and `staleness` in full and traced both return shapes.

### MINOR — `staleness()` returns two different dict shapes; the missing-index one has no `behind`, and its escalation message contradicts itself

**Where:** `src/weave_index.py:449-452` (the `except OSError` branch) versus lines 515-518,
and `src/weave_index.py:546`.

**What:** the no-index branch returns `{"exists", "age_hours", "modified_since",
"total_records", "stale", "reason"}` — **no `behind` key**. The normal branch returns
`behind` as well. And `escalate_if_stale` formats
`"... is %s -- %.1f hours old"` with `st["age_hours"] or 0.0`, so when the index is absent
the filed work order's `what` text reads **"data/ENTITY_INDEX.json is missing -- 0.0 hours
old"**.

**Why it is wrong:** (a) any consumer other than `escalate_if_stale` that reads `st["behind"]`
— the field the module puts there for the open owner question — gets a `KeyError` in exactly
the case where the index does not exist; (b) "missing" and "0.0 hours old" cannot both be
true, and the `what` text is what a person reads off the RUN queue to decide what to do.
`evidence` carries the honest `None`, so the data is right and only the prose is wrong.

**Confidence:** read both return statements and the format expression; `age_hours` is `None`
on that branch by construction, and `None or 0.0` is `0.0`.

### MINOR — `escalate_if_stale()` is unguarded and sits in front of the rebuild it exists to demand

**Where:** `src/weave_index.py:536` (`import workorders as WO`) and `src/weave_index.py:576`
(`_order = escalate_if_stale()` in `main()`, before `build()` at line 581).

**What:** neither the import nor the `WO.file_order(...)` call has a handler, and `main()`
has none around line 576.

**Why it is wrong:** the escalation exists precisely because *nothing schedules the rebuild*,
so the hand-run `python src/weave_index.py --write` is the only remedy in existence. An
unimportable or raising `workorders` therefore takes down the remedy on the way to reporting
that the remedy is needed — the staleness grows, the next hand run hits the same
`workorders` fault, and the only way out is to notice that the failure is in the reporter
rather than the builder. `file_order` itself is well-behaved on the ordinary failure (it
returns `None` and writes to stderr, `src/workorders.py:557-563`), but it raises `BadOrder`
on validation and `_mutate` can raise; the point is that a *reporting* side-check is
unconditionally ahead of the *work* in a module whose work has no other scheduler. A
`try/except` here, with the failure said out loud, would cost nothing and is the discipline
`render_views` applies in `publish.py` for the same reason ("IT CANNOT STOP A PUBLISH").
Filed as MINOR rather than MAJOR because I could not produce a live raise.

**Confidence:** read `escalate_if_stale` and `main()`; read `workorders.file_order`'s tail
(`src/workorders.py:530-564`) to establish its no-raise path and its two raising paths.

### MINOR — `compress_store.store()` sweeps its uniquely-named temp on a denied rename but not on a failed write

**Where:** `src/compress_store.py:54-56` against the cleanup at `src/compress_store.py:70-75`.

**What:**
```
tmp = "%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())
with open(tmp, "wb") as f:
    f.write(blob)
landed = silence.replace_retry(tmp, path)
if not landed:
    try: os.unlink(tmp) ...
```
The `open`/`write` is bare. Only the *replace-denied* path unlinks.

**Why it is wrong:** the temp name deliberately carries pid **and** thread (comment at lines
49-51), so failures accumulate uniquely-named files instead of overwriting one — and the
cleanup added under order `bf22c557852e` says exactly that: *"repeated denials on a hot path
accumulate UNIQUELY-NAMED files instead of overwriting one, and nothing else in the kit ever
comes back for them."* A write that raises (disk full, a denied create, an interrupted
`f.write`) leaves the same uniquely-named litter in the chapter store and the same nothing
comes back for it. The house form is three lines away in this batch:
`publish._write_text_atomic` (`src/publish.py:1259-1275`) wraps the write, removes the temp,
and re-raises. Only the argument was applied here; only one of the two exits was.

**Confidence:** read the function in full; compared against `publish._write_text_atomic` and
`silence.write_json`'s own `_discard_tmp` discipline as cited at `src/sweep_plan.py:590-591`.

### MINOR — a `--batches` stderr line in `sweep_plan.main()` cannot say that `n` was ignored

**Where:** `src/sweep_plan.py:1013` and `src/sweep_plan.py:1048-1051`.

**What:** `plan_rec = freeze_plan(a.run, a.batches)`; `freeze_plan` returns an existing plan
unchanged when one is frozen; `main()` then prints `# plan for run=%s is FROZEN at %s`.

**Why it is wrong:** `python src/sweep_plan.py --batches 24 --run run55` against an already
frozen 16-batch plan prints 16 batches and the word FROZEN, with no line saying that 24 was
asked for and not honoured. The counts line above it (`# %d modules, %d lines, %d batches`)
is derived from `plan`, so the numbers are honest — but a coordinator who typed `24` has to
notice the discrepancy themselves. Reported as a QUESTION about whether the idempotency
should be *loud*, not as a fix: refusing would break the documented "re-running the dispatch
command cannot silently re-shuffle a run" property.

**Confidence:** read `freeze_plan` and the `--batches` arm of `main()` line by line.

### MINOR — `sweep_plan.record()`'s shard write is loud when the rename is denied and quiet when the write raises

**Where:** `src/sweep_plan.py:518-524` (denied: `silence.note` **plus** a full stderr
paragraph telling the batch to call `record()` again) against `src/sweep_plan.py:536-540`
(the outer `except Exception` around the whole shard write: `silence.note` only, no print,
no cleanup of the half-written `tmp`).

**What:** `os.makedirs` failing, `open(tmp, "w")` failing, or `json.dump` raising on an
unserialisable `covered` all land in the silent arm.

**Why it is wrong:** the comment on the loud arm is the argument for the quiet one too — *"a
lost shard ... makes a batch that DID its work unprovable, and the sweep's completeness check
then blames an agent that read every line. Said out loud so the caller can re-record."* A
shard that never got written at all has exactly that consequence and the caller is told
nothing; `record()` still returns the merged aggregate dict, which reads as success. The
half-written `tmp` is also left behind (the `os.remove(tmp)` at lines 531-534 is inside the
denied-rename branch only).

**Confidence:** read `record()` in full and traced which statements each handler covers.

### MINOR — `burgs.py`'s header cites `:301` for a figure that is at `:318`

**Where:** `src/burgs.py:49` and `src/burgs.py:52` ("a file whose own body already said 5,986
at `:301`" / "The 5,986 at `:301` is correct as written"), against the actual occurrence at
`src/burgs.py:318`.

**What:** line 301 is `worlds = WS.build_all()`. The "5,986 worlds carry 5,939 distinct
designations" sentence the header is defending is seventeen lines further down, inside the
order `65ae84ee4bd7` comment.

**Why it is wrong:** finding-type 4, and pointedly so — the paragraph carrying the stale
citation is order `d5a06f9c6dee`'s own repair of a header that had drifted out of step with
the body of the same file, and it drifted again in the one dimension it did not check. A
reader following `:301` to decide whether the header's `~6,000` and the body's `5,986`
describe the same measurement lands on an unrelated line of code.

**Confidence:** `grep -n` for every occurrence of the figure in the file, then `sed -n
'299,303p'` to read what `:301` now holds.

---

## INFO

### INFO — `address._load_spine_codes` accepts any JSON shape

**Where:** `src/address.py:33-37`. No `isinstance(_SPINE_CODES, dict)` check. A
`CHARTER_SPINE_CODES.json` holding a list would pass `source_name in codes` (list membership),
then raise `TypeError` on `codes[source_name]` or `AttributeError` on `codes.items()`. It
fails rather than inventing an address, so the direction is safe — recorded only because
`scout.py` and `weave_index.py` in this same batch both state the rule explicitly
("wrong-shape is the same fact as unparseable") and this module, which Hard Rule 2 governs,
does not. Verified the live file is a 220-entry dict with no empty values.

### INFO — `address.spine_code_for`'s two fallbacks disagree on how they test their own result

**Where:** `src/address.py:266` (`if best_code is not None: return best_code`) against
`src/address.py:300` (`if best:`). The second is a truthiness test on a spine code string,
so an empty-string code in the Acquisitions Index would be silently discarded and the source
would fall to `UNASSIGNED`. Checked the live data: 0 of 220 codes are empty, so this is
latent, and `UNASSIGNED` is the safe direction anyway.

### INFO — `cosmology_graph.main()` sizes the cluster listing from the pair count

**Where:** `src/cosmology_graph.py:182` computes `shown` from `len(ranked)` (pairs), and
`src/cosmology_graph.py:197` reuses it as `comps[:shown]`. With `--show 16` against a graph
of 5 pairs, `shown` is 5 and only 5 clusters print. The "... N further clusters not printed
here" line at 201-203 *does* disclose it, so this is not a Hard Rule 0 truncation — it is one
name doing two jobs, and the flag's help text ("how many ranked rows to print on screen")
does not describe the behaviour the cluster block gets.

### INFO — `cosmology_graph.components()` omits sources with no edge above the threshold

**Where:** `src/cosmology_graph.py:142-163`. `adj` is built only from pairs at or above
`threshold`, and the component walk iterates `adj`, so a source that co-attests entities but
whose every pair falls below the floor appears in `source_entities` and in `pairs` and in no
cluster at all — not even as a singleton. Defensible (a cluster of one is not a cluster), but
`cluster_count` in the written artifact is therefore not a partition of the sources, and
nothing in the file says so.

### INFO — `publish._is_compiled` is called with a bare filename where its docstring describes a path

**Where:** `src/publish.py:527-530` (docstring: *"any `__pycache__` path component, or a
`.pyc`/`.pyo` file"*) versus the call at `src/publish.py:583` (`if _is_compiled(f): continue`,
where `f` is a filename from `os.walk`). The `__pycache__`-component half of the predicate can
never fire at that call site. Harmless — the walk prunes `__pycache__` from `dirs` at line 580
— but the function reads as doing two things at a site where it does one.

### INFO — `navtree.main()` labels every zero-world node as "branches holding sources but no catalogued worlds yet"

**Where:** `src/navtree.py:258-261`. `empty` is `[k for k, v in nodes.items() if v["n"] == 0]`,
which is every node no world passed through, regardless of whether it holds sources.
Reading the two `touch` loops (`src/navtree.py:96-113`), every node is incremented by one loop
or the other, so today `n == 0` does imply `src > 0` and the label is true. It is true by a
property of the build rather than by the test, and a third contributor to `nodes` would make
the printed sentence wrong without anything failing.

### INFO — `navtree`'s root sort assumes integer-spelled hyperverse keys

**Where:** `src/navtree.py:213` (`sorted((k for k in out if "." not in k), key=int)`).
`SEVENFOLD.json`'s `hyperverse` values feed this via `touch`; a non-numeric spelling raises
`ValueError` out of `build()`. Fail-closed, and the file is generated, so recorded only.

### INFO — `compress_store`'s zstd probe catches `ImportError` only

**Where:** `src/compress_store.py:12-17`. A `zstandard` whose native extension fails to load
with something other than `ImportError` escapes at import time and takes down every module
that imports `compress_store`. Given this machine's documented interference with native
installs it is worth knowing; it is not a demonstrated failure.

---

## Read and found nothing to report

* **`src/burgs.py`** (aside from the `:301` citation): checked `_rank_at_or_above` for the
  `k = 0` divide-by-zero in `rank_population` (both `while` loops guard it correctly),
  checked `class_histogram`'s reversed-`CLASSES` block accounting against `classify`'s
  half-open intervals (they agree; `lo = 0` short-circuits via the `lo <= HAMLET_FLOOR`
  arm), checked that `burgs_for`'s `stop = n if limit is None else max(0, min(int(limit), n))`
  cannot fabricate or silently widen (order `1bc825e806a9` holds), and checked that
  `main()`'s numerator and denominator come from the same pass (they do — `total` and `cls`
  are both accumulated in the one loop over `worlds`, and `per_world` is a list-valued dict
  so the `65ae84ee4bd7` collision loss is really closed).
* **`src/cosmology_graph.py`** (aside from the two INFOs): checked the weight formula against
  the docstring's stated `1/log(n+1.5)` with the `×0.15` ubiquity penalty (they match,
  `src/cosmology_graph.py:123-125`), checked that no filter stands between `pair_w` and the
  written `pairs` list (`pairs_filtered: False` is honest — `ranked` is the whole of
  `pair_w.items()`), checked the `--write` verdict gate and its `return 1`, and checked that
  all four string cuts now go through `_cut` with a marker.
* **`src/navtree.py`** (aside from the two INFOs): checked `audit()`'s children-sum arm for
  the KeyError its comment says it avoids, checked that no node can hold both `k` and `w`
  (the worlds loop reaches depth 5 and only depth-5 nodes get `w`), checked both hash-order
  tie-breaks (`register_for`, and the grounding pick at line 187) really are deterministic,
  checked `sources_under`'s `+ "."` on both `startswith` arms, and checked that both
  `--write` refusal paths and the audit-record denial all return `1`.
* **`src/address.py`** (aside from the two INFOs): traced all four matching branches in
  `spine_code_for` and re-derived the `_index_name_is_placed_like_a_title` remainder
  arithmetic by hand for the opening, closing and exact-equality cases; confirmed
  `_worded`'s space padding makes `evidence = min(len(...))` equal to the matched text;
  confirmed `tier_for`'s ascending-floor loop yields the highest qualifying rung;
  confirmed `promote` never demotes and that `tier_rank(earned)` can never be `None`;
  confirmed `_FILLER`'s reachable subset is exactly the six entries left, as order
  `7b9d3605a8a4` claims, and that the open question about the `len(w) > 1` filter is marked
  kept-on-purpose.
* **`src/publish.py`** (aside from the findings above): read the secret scanner's three locks
  end to end, including `_scan_units`'s overlap arithmetic at a segment boundary (`carry`
  is re-seeded per segment and cleared on a real line break — a credential lying across a
  block boundary is seen whole), `_is_real_secret`'s structural-versus-ambiguous split and
  the case-insensitive `_AMBIGUOUS` fix, the per-line `FIXTURE_MARKER` rule in both
  `scrub_text` and the scanner, and `_scrub`'s key-collision suffix. Confirmed the
  `UNSCANNABLE` finding is **not** filtered out by `push()`'s `startswith('SUPPRESSED')`
  filter, so an unreadable *file* genuinely blocks the push. Confirmed there is no active
  `secret_scan` suppression in the table (the only mention anywhere is `drill.py:4585`
  asserting the negative). Confirmed all three fail-closed import guards in `push()`
  (`ledger_guard`, `mutate`, and `escalation` in `main()` plus the per-cycle re-import),
  the both-sides-of-the-copy mutation reading, the `_same_dir`/marker double gate on every
  delete path, the marker-before-prune ordering, and the `prune_export` `None`-vs-`0`
  distinction reaching stdout. `maintenance_shift_live`'s fail-open is argued in its own
  docstring and is loop-mode only; noted and left.
* **`src/sweep_plan.py`** (aside from the findings above): checked `_src_py_files`'s
  `os.walk` really descends into `src/deprecated/`, `normalise_module`'s exact-then-ambiguity
  refusal, `record()`'s per-shard write topology and the argument that `SWEEP_COVERAGE.json`
  is a derived view whose verdict may be discarded (it holds — `covered_by` unions from
  shards and only *adds* from the aggregate), `covered_by`'s membership-not-newest-wins
  semantics, `roster_of`'s `None`-versus-empty distinction, `missing_detail`'s refusal to
  infer from mtime, and `check_briefs`'s `clean` (it does cover `undispatched`, because those
  batches' modules land in `uncovered`). `coverage_map` and the removed `latest_run` are
  both marked kept/removed by owner ruling; saw the markings and moved on.
* **`src/scout.py`** (aside from the two findings above): checked `_mutate`'s CAS loop
  including the wrong-shape and unreadable refusals and the pid+thread+attempt temp name,
  `verify`'s `needed = max(1, min(MIN_NAME_HITS, probeable))` against `_names_in`'s
  `len(n) < 4` skip (the two agree, and the `probeable == 0` unverifiable arm closes the
  mirror case), `_ask`'s `(answer, why_not)` pair and the `None`-is-not-an-answer arm,
  `scout()`'s three-state `registered` and the gating of host adoption on page registration,
  `sweep()`'s `seen_ok` guard on `_unstamp` and `_unstamp`'s `!= now` check against a
  concurrent stamp, and the archive-before-trim ordering in the log roll-off. One cosmetic
  inconsistency noted and not filed: `scout()` filters `probeable` on the raw name's length
  (`src/scout.py:398`) while `verify` and `_names_in` filter on the stripped length — `verify`
  recounts, so the bar it applies is always the correct one.
* **`src/weave_index.py`** (aside from the findings above): checked `designations()`'s
  do-not-cache-a-failure fix and its `cacheable` guard, `_records_sig`'s per-file
  `continue`-and-finish-the-walk behaviour and the `unstattable` forcing of `sig=None`,
  `load_records`'s signature-gated cache, `norm`'s conditional-expression precedence
  (`(s + "@" + keep) if keep else s` — correct), `build()`'s uncapped descriptions and its
  counted `excluded` bucket, the relocation of both the short-key and `_STOPNAMES` matching
  rules out of `build()` and into `main()`'s candidate loop with their casualties printed,
  the all-buckets spread histogram, the marked `TOP_N` cut with its stated floor, and the
  paired atomic `--write` with its SPLIT diagnosis and `return 1`.
* **`src/compress_store.py`** (aside from the two items above): `load()`'s address
  verification is sound — `_address_in` only claims a 32-lowercase-hex stem, `content_hash`
  produces exactly that, and a mismatch raises rather than returning text.

---

## Cross-batch citations I could not resolve from inside this batch

Named rather than guessed at or dropped, per the brief:

* `src/weave_index.py:436` claims "`verify_math` already ANNOUNCES this -- twice a run". The
  nearest thing I can see is `weave.load_index`'s `weave.py:index-stale` note, described at
  `src/verify_math.py:1676-1680`. `weave.py` and `verify_math.py` are outside batch 10, so
  whether "twice a run" is still the count is not mine to settle.
* `src/publish.py:561` cites the drill net
  `_the_scanner_reads_files_over_two_megabytes` deliberately without a line number. The net
  exists (`src/drill.py:4621`) and does call `P.scan_for_secrets(d)` with no `only=`; whether
  its three >2 MB fixtures are still >2 MB is a `drill.py` question.
* `src/navtree.py:326` cites "generate.py, weave_index.py, sweep.py, feats.py and
  handbuilt.py all say so at this same line" (order `8605c2ed6061`). `weave_index.py` does
  (`src/weave_index.py:717-721`); the other four are outside this batch.
* Whether `workorders.file_order`'s refresh-not-duplicate behaviour means the
  ENTITY_INDEX order's `last_seen` being refreshed by the very `--write` run that fixes the
  staleness (`src/weave_index.py:576` before `581`) actually matters depends on how the queue
  ages orders out. `workorders.py` is outside batch 10.
