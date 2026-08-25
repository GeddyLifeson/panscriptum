# AUDIT — batch 15 (run30)

Files: `src/local_agent.py`, `src/build_terminal.py`, `src/allsweep.py`, `src/worldseed.py`,
`src/sweep.py`, `src/propagation.py`, `src/scope.py`

Method: every line of every file read top to bottom. Reproductions used a scratch temp dir and
read-only synthetic-string calls against pure predicates (`_safe()`, `t_propose_patch(..., apply=False)`
with a non-matching `find` string so no write is ever attempted); one reproduction ran the real,
read-only `sweep()`/`report()` logic against live data (no write — `main()`/`silence.write_json`
was never invoked). Nothing in this audit wrote to the repo. `local_agent.py` was never executed
as a script; it was imported as a library purely to call its own path/gate functions.

**Secrets: none found.** Grepped all seven files for api key / secret / password / token /
bearer / AKIA / `sk-` patterns — the only hits were the English words "token" and "token_flow"
inside comments, no credential material.

---

## 1. src/local_agent.py

Overall: this file already carries an unusually thorough remediation history in its own comments
(four prior denylist bypasses — case-folding, name-prefix, NTFS alternate-data-stream, extension
case — documented and fixed by runs #23–#25, plus the M24 whole-region allowlist added 2026-08-25).
I re-verified all four of those fixes hold (see 1.4) and found one further bypass of the same
shape that is **not yet covered**.

### 1.1 [HIGH] [REPRODUCED] NTFS 8.3 short-filename alias bypasses the module DENYLIST — `_safe()`/`t_propose_patch()`, :293-331, :453-514

`t_propose_patch()` derives `modname` from `os.path.basename(full)[:-3]` and matches it
case-folded against `DENYLIST` (`{"foreman","silence","health","allsweep","estate","standards",
"verify_math","local_agent","pipeline","runguard","gpu_lane","sweep_plan"}`). This machine has
8.3 short-name generation enabled (confirmed: `fsutil` shows `STANDA~1.PY`, `VERIFY~1.PY`,
`LOCAL_~1.PY`, `SWEEP_~1.PY`, `CONFIG~1.YAM` for any denylisted file whose real name is 9+
characters before the extension). `_safe()` resolves these purely lexically — it never asks the
filesystem for the canonical long name — so `path="src/STANDA~1.PY"` resolves to the *same file*
as `standards.py` (`os.path.isfile` is True) while `modname` comes out `"STANDA~1"`, which is not
in the denylist under any case fold.

Reproduced end-to-end against the real files, read-only (`apply=False`, a `find` string chosen to
occur zero times so no write is ever attempted — the function still runs every check up to that
point):

```
src/STANDA~1.PY  -> {'applied': False, 'error': 'find string occurs 0 times...'}   # denylist NOT hit
src/LOCAL_~1.PY  -> {'applied': False, 'error': 'find string occurs 0 times...'}   # denylist NOT hit
src/SWEEP_~1.PY  -> {'applied': False, 'error': 'find string occurs 0 times...'}   # denylist NOT hit
src/VERIFY~1.PY  -> {'applied': False, 'error': 'find string occurs 0 times...'}   # denylist NOT hit
src/pipeline.py  -> {'applied': False, 'error': 'pipeline is on the denylist...'}  # control: real name IS caught
```
By contrast, `src/foreman.py`, `silence.py`, `health.py`, `allsweep.py`, `estate.py` (≤8 chars
before `.py`) get no distinct 8.3 alias on this volume and remain fully protected.

Whether a real write is currently achievable depends on an accident, not a design guarantee: with
`apply=True` and a genuinely matching `find`, the write to the aliased path lands on the real
denylisted file's bytes, and `_gates()` runs unconditionally afterward. For a `.py` file it then
attempts `import STANDA~1` (etc.) as the import-gate — and `~` is not legal in a Python identifier,
so that specific gate throws a `SyntaxError` and the patch is reverted:
```
>>> import STANDA~1
SyntaxError: invalid syntax
```
So for the four currently-affected files this happens to end safely — **but only because every
one of them needs 8.3 truncation, which always inserts a `~`.** This is not a designed protection:
`ast.parse` and `pyflakes` both run and pass *before* the import gate (they check file content,
not the name used to open it), so gate 1 ("is this file on the denylist") is not actually
enforced — it is skipped, and the write to the protected file's real bytes genuinely happens on
disk before any gate fires. If a future denylisted `.py` module's basename happens to fit 8.3
without truncation-needing-a-tilde (unlikely given current names, but not excluded by any
invariant here), or if a non-`.py` denylisted path ever sits under a `WRITABLE_PREFIXES` root, or
if the process is killed in the write→gate window (the same "half-patched module on disk" failure
mode this file's own comments at :538-556 already worry about for a *failed revert*), this becomes
a real corruption of the checking machinery the denylist exists to protect. This is the fifth
instance of "a gate keyed on a STRING while the filesystem resolves a DIFFERENT string to the same
object" — the file's own docstring at :306 names this exact pattern as "m113 and m114's shape a
third time"; 8.3 aliasing is a fourth/fifth instance not yet enumerated there.

**Fix**: resolve the canonical long name before deriving `modname` — `os.path.realpath()`
does not do this on Windows for 8.3 aliases; use `win32api.GetLongPathName` (pywin32) if
available, or reject any path component matching the 8.3 alias shape (`^[^.]{1,8}~\d+\.[^.]{0,3}$`
after normalizing) the same way trailing-dot/space and ADS components are already rejected at
:313-320.

### 1.2 [MEDIUM] [REPRODUCED by inspection] Docstring says four tools; the code hands the model six — :9-14 vs :136-193

The module docstring lists exactly four tools (`read_file`, `list_dir`, `grep`, `propose_patch`).
The actual `TOOLS` list defines **six**: those four plus `find_symbol` (:170-178) and `run_check`
(:179-192). `run_check` in particular is not a cosmetic addition — it lets the model execute
`verify_math`/`pyflakes`/`compile`/`silence` — worth documenting where a reader is told what
capabilities the model has been handed. Not a security hole (both undocumented tools are
correctly gated: `run_check` is allowlisted to `_CHECKS` and read-only by construction; `find_symbol`
is read-only), but it is exactly the "comment says X, code does Y" class this sweep is asked to
catch, and an operator reading only the docstring would materially undercount the model's surface.

**Fix**: update the docstring's four-item list to six, or fold `find_symbol`/`run_check` under a
"and two read-only introspection tools" line.

### 1.3 [MEDIUM] [HYPOTHESIS — not tested] Unlocked concurrent `propose_patch` on the same file — :515-557

`t_propose_patch()`'s apply path is read-original → write-patched → run `_gates()` → on failure,
write-original-back — all via plain `open(full, "w")`, no file lock, no re-check that the file is
unchanged since `original` was read. Two concurrent `local_agent.py` invocations (or one invocation
racing a human/editor save) targeting the same writable file can interleave: process B's write can
land between process A's write and A's revert, and A's revert then silently discards B's change
(or vice versa) with no error surfaced to either caller — B is told `{"applied": True}` for a
change that no longer exists on disk. Not reproduced (would require two real concurrent writes,
which this audit is not permitted to perform against repo state), but the code has no mechanism
that would prevent it, and the project's own `data/` write paths take this hazard seriously
(`silence.replace_retry`'s docstring, `silence.write_json`'s PID+thread temp name). `local_agent.py`
is the one write path in this batch that touches live source files and has no equivalent guard.

**Fix**: hold a lock file (e.g. `state/local_agent.lock` via `silence`-style atomic create) for the
duration of read→write→gate→(revert), or re-read and diff the file immediately before the backup
write to detect a concurrent modification and abort instead of silently reverting over it.

### 1.4 Confirmed fixed / working as documented

- `_safe()` correctly refuses `..`-traversal, sibling directories whose name merely starts with the
  project's name (`panscriptum-library-kit-EVIL`, `...-export`), absolute paths, UNC paths
  (`\\server\share\...`), the `\\?\` extended-length prefix, NTFS ADS (`::$DATA`), trailing dot/space
  components, and `.git/`. All tested against synthetic strings; all returned `None`.
- `t_propose_patch()`'s WRITABLE_PREFIXES allowlist genuinely fails closed: tested `data/records/`,
  `state/`, `output/index/`, `reference/keystone_volumes/` (including via `..`-traversal from inside
  `src/`, `prompts/`, `handoff/`, and via case variation `REFERENCE/KEYSTONE_VOLUMES/`) — every one
  refused with "outside the writable surface", *before* the DENYLIST_PREFIXES check even runs. The
  region protection docstring's claim holds.
- `config.yaml` is denied via `DENYLIST_PATHS` on its real name, and is separately unreachable via
  the allowlist (it sits at repo root, outside `src/`, `prompts/`, `handoff/`) even via its own
  8.3 alias `CONFIG~1.YAM` — confirmed by direct test, the allowlist step catches it regardless of
  the 1.1 bypass because config.yaml was never protected *only* by the name-denylist.
- `pipeline`, `runguard`, `gpu_lane`, `sweep_plan` are all present in `DENYLIST` (:52-65) as the
  task asked to confirm. Verified by direct read and by test (`src/pipeline.py` and `src/PIPELINE.py`
  both correctly refused).
- `propose_patch` cannot create or write `data/records/*.json` directly under any path spelling
  tried (see above) — confirmed.
- The docstring's own narrated history of the "gates skipped for non-`.py` files" bug (the task's
  hinted :406-407 item) is **already fixed** in current source: `_gates()` (:384-450) now runs the
  parse/lint/import checks per-format and runs `verify_math` unconditionally for every file type,
  and `t_propose_patch()` calls `_gates(full, modname)` unconditionally after every write regardless
  of `modname`. The line numbers in the task's hint (406-407) fall inside the pyflakes-subprocess
  call in the current file, not the `modname` derivation — the bug those numbers described has
  moved/been fixed; I could not reproduce it.
- The revert-failure path (:536-557) correctly reports `"reverted": False` and an `ALARM` when the
  write-back itself fails, rather than always claiming `"reverted": True` (the bug the surrounding
  comment describes as previously present is not present now).

---

## 2. src/allsweep.py

### 2.1 [HIGH] [REPRODUCED] `check_import()` reclassifies a genuine `raise SystemExit(...)` guard failure as a healthy module — :98-119

```python
if "Traceback" not in (r.stderr or ""):
    ok, err = True, "no CLI (imported cleanly)"
```
`raise SystemExit(msg)` with a string argument prints only the message to stderr and exits 1 —
Python does not print a traceback for it. So *any* module-level guard that legitimately aborts via
`raise SystemExit(...)` — including this project's own `_BAD_CHARS` corruption guard, present
verbatim at the top of this very file and of `local_agent.py`, `sweep.py`, `scope.py`, and others —
is indistinguishable, from this function's point of view, from "a module with no argparse, exiting
nonzero on `--help` because it has no CLI." Both produce `rc=1` and a stderr with no `Traceback`.

Reproduced with a scratch module:
```python
raise SystemExit(__file__ + ": a regex escape was eaten in transit.")
```
run with `--help`, then classified with `check_import`'s exact logic:
```
returncode: 1
stderr: '...fakemod.py: a regex escape was eaten in transit.\n'
FINAL CLASSIFICATION -> ok: True   detail: 'no CLI (imported cleanly)'
```
This is precisely "a check that cannot fail" — the highest-value category this sweep asks for. If
the `_BAD_CHARS` guard ever actually fires on a real corrupted file in `src/`, the IMPORT tier —
the tier `main()` prints as "N/M import and parse their CLI cleanly" and folds into the top-line
`bad` count — will report that module as fine. The corruption would only surface if something else
happened to import that exact module and crash loudly elsewhere, or a human ran it directly.

**Fix**: distinguish "no CLI" from "aborted for cause." A `SystemExit` raised with a non-empty
string message before any `argparse` object exists is a guard firing, not an absent CLI; a cheap
signal is to special-case `rc==1` and check whether stderr's last line matches the module's own
`__file__` (the `_BAD_CHARS` guard's message format, and a decent proxy for "this exited during
module-level code, not inside `argparse`"), or simply have `check_import` also try `python -c
"import <mod>"` (no `--help`) as a second, unambiguous signal — a raised `SystemExit` guard fires
identically on plain import, while a module with no CLI at all imports clean and does not exit.

### 2.2 [MEDIUM] Self-disclosed: `reconcile()`'s `note()` carries no severity — :161-320, :447-464

Confirmed as described: every `reconcile()` finding — from "ENTRIES BANDED ABOVE THEIR OWN SOURCE'S
CEILING" to "running: dashboard.py" — goes into one undifferentiated list via `note(kind, detail,
n)`, and `main()` deliberately does not fold this tier into the `bad` exit-status count (:447-454
explains why, and says giving it severity is tracked in NEXT_STEPS). This means a genuine cross-
subsystem contradiction found by reconcile — the *only* tier that catches disagreement between two
otherwise-healthy verifiers — cannot fail a CI-style gate on its own; a human has to read the
printed rows. This is a real gap in the "checks that cannot fail" sense, but it is honestly
disclosed in the code (unlike 2.1, which reports a false-positive silently). Rating it MEDIUM
rather than HIGH because the code is transparent about the gap and it is on record as planned work;
still worth prioritizing given how much of the file's own stated purpose ("the next eighteen faults
live" in reconcile's disagreements) depends on it.

### Clean

- `run_verifier()` correctly distinguishes a verifier's own findings (nonzero exit, its documented
  contract) from a real crash (`Traceback` in output) or timeout, and records both via `silence.note`.
- `main()`'s ATOMIC write comment and use of `silence.write_json` for `ALLSWEEP.json` is correct and
  matches the file's own past-tense narration of the m100-class truncate-then-fill bug it fixed.
- The LINT tier fix described in the :440-446 comment (lint findings now flow into the `bad` count
  and into the JSON) is present and correct as written.

---

## 3. src/sweep.py

### 3.1 [HIGH] [REPRODUCED against live data] The funnel docstring's "strictly smaller set" claim is false, and `report()` prints a garbled double-negative when it is — :7-22, :176-233

The module docstring (and the printed header, :14) states each funnel stage —
`catalogued → addressed → reachable → read → evidenced → assayable` — is "a strictly smaller set
than the one above." It is not: `catalogued` is a per-*entry* flag (`e.get("catalogued")`, set by
phase 2's judgment of that specific entry) and `addressed` is a per-*source* fact (`bool(shelfmark)`,
true whenever the entry's *source* has any navtree shelving at all, via `where.get(src)` — :140-151).
These are independent properties; nothing in `sweep()` enforces that an addressed entry must also
be catalogued, or vice versa.

Reproduced directly against live data (read-only — used `sweep.py`'s own row-building logic and
`pipeline.records()`, never called `main()` or wrote `CHARACTER_SWEEP.json`):
```
n total Person entries: 51,904
catalogued:              32,366
addressed:               51,828      <- LARGER than catalogued, contradicting the docstring
addressed-but-not-catalogued: 19,538
```
`report()`'s drop-printing logic (:192-198) is:
```python
drop = prev - f[k]
... + (f"   -{drop:,}" if drop else "")
```
With `prev = f['catalogued'] = 32,366` and `f['addressed'] = 51,828`, `drop = -19,462` (a negative
number, meaning the funnel *widened*, not narrowed). The f-string then renders `f"-{-19462:,}"` —
literally reproduced:
```
addressed drop line (report()'s exact formatting):    --19,462
```
A double-negative on the "addressed" line, printed beside a `#`-bar sized as if it were a shrinking
funnel. (The task's hinted figures — 17,229/49,532 — are close in shape but not exact; the corpus
has grown since that measurement was taken. The defect itself reproduces exactly against current
data.)

**Fix**: either (a) rewrite the docstring/funnel model to acknowledge `catalogued` and `addressed`
are orthogonal facts, not nested stages — printing them as two separate axes rather than one funnel
— or (b) if the intent really is a strict funnel, gate `addressed` on `catalogued` in `sweep()`'s
row construction (`shelf = shelf if row["catalogued"] else None`) so the funnel actually holds the
invariant it claims. Either way, `report()` should clamp or specially format a negative `drop`
rather than blindly prefixing `-`.

### Clean

- `load()`'s docstring-vs-code split of "expected absent file" vs "genuinely corrupt cache" (:68-96)
  is implemented correctly and is a good example of the opposite of 2.1/3.1 — a comment that
  accurately describes non-obvious behavior.
- `main()`'s use of `silence.write_json` with an explicit check of the return value (:249-252),
  including printing a clear stderr warning and returning exit code 1 when the atomic replace is
  denied, is the correct, safe pattern — worth holding up against `worldseed.py`'s violation below.

---

## 4. src/propagation.py

### 4.1 [LOW] [REPRODUCED by inspection] Stale comment names a constant that no longer exists — :53

```python
# BASE_YEARS_PER_HOP: how long news takes to cross one intermediary shelf. Anchored to the
```
No `BASE_YEARS_PER_HOP` is defined anywhere in this file. The very next paragraph in the same
comment block (:56-60) explains why: "the first draft counted HOPS... Distance is now the summed
inverse of shared evidence." The constant that survived the correction is `YEARS_PER_UNIT_DISTANCE`
(defined :65), a genuinely different quantity (per unit of graph *distance*, not per *hop*). The
comment header was never updated to match the code below it — confirmed exactly as the task's
hinted line number describes.

**Fix**: retitle the comment `YEARS_PER_UNIT_DISTANCE:` and adjust the prose to distance rather than
hops (the surviving text about the 400–900 AS anchoring and the 1.0-distance-per-millennium scale
is still accurate and does not need to change, only the header).

### 4.2 [Characterisation, root cause out of batch] `propagation.py` is clean; it correctly and faithfully reports a graph that has already lost 71% of its edges before propagation ever sees it

`propagation.py` itself has no filter or cap of its own — `load_graph()` (:71-82) reads every pair
in `data/SHARED_STAGE_GRAPH.json` exactly as written, with no threshold, no truncation, no sampling.
The defect is entirely upstream, in `src/cosmology_graph.py` (not in this batch, flagged here only
because the task asked to characterise propagation's side):

```python
# src/cosmology_graph.py:143-154, the --write path
"pairs": [... for (a, b), w in sorted(pair_w.items(), ...) if w >= 1.0],
```
This `if w >= 1.0` is an **undisclosed write filter** — nowhere in the module's docstring or in the
comment immediately above this line (which discusses atomicity, not the threshold) is the cutoff
named or justified. Reproduced against live data (read-only, via `cosmology_graph.build_graph()`,
never called `--write`):
```
total co-attesting source pairs (build_graph): 3,753
pairs with w >= 1.0 (survive the write filter): 1,087
pairs DROPPED by the undisclosed w>=1.0 filter: 2,666 (71.0%)
sources reading as TOTALLY DISCONNECTED after the filter: 25
```
(Confirmed the on-disk `SHARED_STAGE_GRAPH.json` matches this freshly-computed filtered set exactly
— this is the current live state, not stale.) The 25 casualties include real, populated sources:
`2112 (Rush)`, `Rainbow Six`, `Warhammer Fantasy`, `Xanathar's Guide to Everything`, `Ghosts of
Saltmarsh`, `the Lovecraftian mythos`, and 19 others.

**Effect inside propagation.py**: `shortest(adj, src, dst)` for any of these 25 sources returns
`(math.inf, [])` **unconditionally**, and `main()` prints `"DISCONNECTED (no shared furniture at
any remove)"` (:176-177). This is indistinguishable, from propagation's own output, from a source
that genuinely shares zero attested entities with anything else in the library — but 24 of the 25
*do* co-attest at least one entity with something; the evidence was simply thrown away below weight
1.0 before propagation ever got a chance to compute a (long but finite) distance from it. Given this
module's own stated purpose — "the claim becomes falsifiable... if the number says Black Ops SHOULD
have heard of a thing, the entry must explain why it did not" (:29-31) — a source reporting
DISCONNECTED for this reason is not a falsifiable finding, it is a threshold artifact wearing the
shape of one, and Hard Rule 0's own language applies almost verbatim: "a cap does not fail, it
returns a smaller universe wearing the same shape as the real one."

This finding belongs to whichever batch covers `cosmology_graph.py`; flagging it loudly here because
it directly determines what a reader of `propagation.py`'s output will conclude.

---

## 5. src/scope.py

### 5.1 [MEDIUM-HIGH] [HYPOTHESIS — not tested] Unlocked read-modify-write on `SCOPE.json` — `build()`, :102-120

```python
def build(records, hosts):
    out = {}
    if os.path.exists(OUT):
        out = json.load(open(OUT, encoding="utf-8"))
    todo = sorted({h for s, h in hosts.items() if h and h not in out ...})
    for i, h in enumerate(todo, 1):
        ... out[h] = sc ...
    silence.write_json(OUT, out, indent=1, ensure_ascii=False)
    return out
```
`out` is read once at the start, then mutated in memory across a loop that makes a live wiki API
call per host (`scope_for()` → `F.api()`/`F.fetch()` — genuinely slow, minutes-to-hours for a full
`todo` list), then written back as a whole in one shot at the end. The final `silence.write_json`
call is itself atomic (correct use of the two-writer-contract write mechanism), but the *read* that
seeds `out` is not protected against a concurrent writer landing in between: if a second `scope.py
--build` (or any other future writer of `SCOPE.json`) reads the same starting snapshot and finishes
first, this process's eventual write silently clobbers every host the other process added, because
this process's `out` dict never saw them — a classic lost-update race, the same "two-writer hazard"
shape the project's own memory notes already name for `data/records/`. Not reproduced (would
require two real concurrent processes writing the real `data/SCOPE.json`, which this audit will not
do); flagged as HYPOTHESIS on the strength of the code structure, which has no lock, no re-read-
before-write, and no optimistic-concurrency check anywhere in the function.

Severity note: `scope.py` is in `allsweep.py`'s `NEVER_RUN` set (invoked deliberately, not by an
automated hot loop), which lowers the practical likelihood versus, say, a scheduled job — but
nothing in the code prevents a human running two builds back to back, or a partial run resumed
from a second terminal while the first is still mid-flight (a very plausible real operator mistake
given this function's own resumability design: it explicitly skips hosts already `in out`, which is
precisely the feature that invites "run it again in another window while the first is slow").

**Fix**: re-read `OUT` immediately before the final write and merge (`out.update(fresh_disk_read |
out)` favoring newly-computed entries), or take a lock file for the duration of `build()`.

### Clean

- `ceiling_for()` and `scope_for()` are pure/read-only and correctly structured; no swallowed
  failures — the one `except Exception: silence.note(...)` at :111-113 is appropriately scoped to
  a single host's scope computation, doesn't abort the whole run, and is correctly recorded rather
  than silently dropped.

---

## 6. src/worldseed.py

### 6.1 [HIGH] [REPRODUCED by inspection + cross-reference] `--write` bypasses `silence.write_json` entirely — a straggler from the project's own already-fixed bug class, on a file two other modules read live — :317-322

```python
if args.write:
    path = os.path.join(HERE, "data", "WORLDSEEDS.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({w["designation"]: {"address": address(w), **w} for w in worlds},
                  f, indent=2, ensure_ascii=False)
    print(f"\nwrote {path}")
```
This is a plain truncate-then-fill write. `worldseed.py` already imports `silence` (:65) and uses
`silence.note()` correctly for read-side exception handling (:250, :258) — but its one actual JSON
write to shared `data/` never goes through `silence.write_json`, in direct violation of this
project's two-writer contract ("shared state ONLY via `silence.replace_retry` / `silence.write_json`").

This is not a hypothetical risk: `silence.write_json`'s own docstring (`src/silence.py:290-301`,
read for context) states the 2026-08-25 comprehensive sweep found and fixed **twelve** call sites
across ten modules doing exactly this — "a reader arriving in the gap sees an empty or half-written
file; a crash in the gap leaves it that way permanently" — and that sweep evidently missed this one.
And `WORLDSEEDS.json` is not a dead-end output: it is read live, unguarded by any atomicity
assumption of its own, by two other modules in the pipeline:
```
src/address_space.py:302   open(os.path.join(HERE, "data", "WORLDSEEDS.json"), ...)
src/pipeline.py:1493       json.load(open(os.path.join(HERE, "data/WORLDSEEDS.json"), ...))
```
`pipeline.py`'s read (checked, :1492-1496) is wrapped in `try/except Exception: silence.note(...);
seeds = {}` — so a truncated file during the write window does not crash `pipeline.py`, but it does
silently zero out every cosmology-seed calculation for that run, recorded only as one more line in
the generic `silence` ledger rather than surfaced as what it actually is (a torn-write data-loss
event on a file this project has otherwise gone to real trouble to protect). `address_space.py:302`
was not fully inspected in this batch (out of scope) so its failure mode on a truncated read is
unconfirmed, but the read itself is unguarded at that line.

**Fix**: `silence.write_json(path, {...}, indent=2, ensure_ascii=False)` — a one-line change,
matching every sibling writer this project has already converted.

### Clean

- `_first()`/`features()`/`to_options()`/`address()` are pure, deterministic, and internally
  consistent — `TEMPLATE`, `CLIMATE_BAND`, and `CULTURE_SET` dict keys were checked against every
  tag `LANDFORM`/`CLIMATE`/`TECH` can produce; no `KeyError` risk found.
- `build_all()`'s 2026-08-24 fix (reading the whole description rather than the first 200 characters,
  :272-279) is present and correctly implemented — a good example of a genuinely-fixed Hard-Rule-0-
  shaped truncation bug, for contrast with 6.1.
- The two `except Exception: silence.note(...)` blocks (:246-259) are appropriately scoped to
  optional enrichment data (`ONOMASTICON.json`, `CONTINUITY_GROUPS.json`) and correctly fall back to
  safe defaults rather than aborting the whole build.

---

## 7. src/build_terminal.py

No correctness bugs, swallowed failures, or contract violations of note. One minor point:

### 7.1 [LOW] Non-atomic write to `output/registry_terminal.html` — :572-573

```python
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
```
Same truncate-then-fill shape as 6.1, but rated LOW rather than HIGH here because — checked —
nothing in `src/` reads this file back programmatically; the one hit for `registry_terminal.html`
outside this file is a documentation table row in `pipeline.py:1357`, not a read. It is a browser-
served static artifact opened by a human, so a crash mid-write would only affect the next person to
open the page in a browser, not another pipeline stage. Still worth the one-line `silence.write_json`
swap for consistency, but does not carry the live-reader risk 6.1 does.

### Clean

- The `<` → `<` neutralisation before splicing catalogue-derived JSON into an inline `<script>`
  block (:561-568) is correct and necessary (a name containing `</script>` would otherwise truncate
  the page), and is honestly commented with its own bug reference (BUGS m10).
- The embedded JS `esc()` HTML-escaper (:85-87) is applied consistently everywhere a catalogue string
  reaches `innerHTML` in the reviewed template — no unescaped interpolation of `DATA`-derived text
  found in the SVG-building code.
- No swallowed exceptions, no writes to any file other than the one declared `OUT`.

---

## Summary table

| # | File | Finding | Severity | Status |
|---|------|---------|----------|--------|
| 1.1 | local_agent.py | 8.3 short-filename bypasses module DENYLIST | HIGH | REPRODUCED |
| 1.2 | local_agent.py | docstring says 4 tools, code has 6 | MEDIUM | REPRODUCED (inspection) |
| 1.3 | local_agent.py | unlocked concurrent propose_patch | MEDIUM | HYPOTHESIS |
| 2.1 | allsweep.py | check_import() misclassifies SystemExit guard as healthy | HIGH | REPRODUCED |
| 2.2 | allsweep.py | reconcile() note() has no severity (self-disclosed) | MEDIUM | REPRODUCED (inspection) |
| 3.1 | sweep.py | funnel docstring false; garbled negative print | HIGH | REPRODUCED (live data) |
| 4.1 | propagation.py | stale comment names nonexistent constant | LOW | REPRODUCED (inspection) |
| 4.2 | propagation.py / cosmology_graph.py (out of batch) | undisclosed w>=1.0 write filter drops 71% of edges, 25 sources read DISCONNECTED | HIGH (root cause out of batch) | REPRODUCED (live data) |
| 5.1 | scope.py | unlocked read-modify-write on SCOPE.json | MEDIUM-HIGH | HYPOTHESIS |
| 6.1 | worldseed.py | non-atomic write to WORLDSEEDS.json, live-read by 2 modules | HIGH | REPRODUCED (inspection + cross-ref) |
| 7.1 | build_terminal.py | non-atomic write, no live readers | LOW | REPRODUCED (inspection) |
