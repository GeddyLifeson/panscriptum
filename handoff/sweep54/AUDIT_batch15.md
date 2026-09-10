# sweep run54 — batch 15 audit

Batch: `local_agent.py`, `escalation.py`, `codewatch.py`, `endpoint.py`, `tiers.py`,
`sevenfold.py`, `resync_roll.py`, `cosmology_graph.py`, `whoruns.py`.

All nine files were read in full, top to bottom (every line), not sampled. `whoruns.py` got the
extra scrutiny the brief asked for: read closely, its helper `overnight._proc_lines` /
`overnight._cmd_tokens` / `overnight.running` / `overnight._in_this_tree` were read alongside it
for comparison, its `drill.py` self-test (`_a_probe_never_counts_itself`) was located and run
directly, and two of its code paths were exercised live in the miniconda interpreter.

I also ran `python src/verify_math.py` in full to see what "one failing row" the brief mentioned
actually is: it is `sweep_plan`'s own completeness proof ("the newest FINISHED sweep proves its
own completeness"), red because `whoruns.py` has not yet been recorded by any *finished* sweep
(run48). That is expected and is not a code defect — it is exactly what my `sweep_plan.record`
call at the end of this batch is for. It does not bear on the two findings below, which are
independent, verified logic gaps in `whoruns.py` itself.

---

## whoruns.py

Read in full. This is the new module; read closely, its docstring's claims checked one by one
against the code, and both suspect paths verified by direct execution rather than by inspection
alone.

### MAJOR — `script_of()` mis-parses a two-token interpreter flag as the script position, producing exactly the false negative this module exists to prevent

**Where:** src/whoruns.py:41-59 (`script_of`)

**What:** The function walks `tokens[1:]` after the interpreter, skipping anything that
`startswith("-")` as "an interpreter flag, keep looking" (comment at line 55), and returns `None`
the first time it meets a non-flag token that does not end in `.py`. Some interpreter flags —
`-X`, in real Python invocations — take their value as a **separate** following argv token
(`python -X utf8 script.py` is argv `['-X', 'utf8', 'script.py']`, not one token). `-X` itself is
correctly skipped as a flag, but the very next token (`utf8`) is a bare non-flag that is not
`.py`, so the loop hits the `return None` branch on line 58 before it ever reaches the real
script argument.

Verified directly:
```
>>> import overnight as ON, whoruns as W
>>> toks = ON._cmd_tokens('C:/py/python.exe -X utf8 src/mutate.py')
['C:/py/python.exe', '-X', 'utf8', 'src/mutate.py']
>>> W.script_of(toks)
None
```
`mutate.py` is genuinely running under this command line and `script_of` reports "no script
here" — the confident-negative failure mode the module's own docstring names four separate times
as this file's entire reason for existing.

**Why it is wrong:** `running()` (whoruns.py:62-89) filters candidate processes through
`script_of`, so any process launched with a two-token interpreter flag before its script path is
invisible to `whoruns.py X.py` — it will print `NONE running X.py` (and `--quiet` exits 1) while
X.py is in fact running. This is the exact "the answer comes back... in the confident direction"
shape the module's own opening paragraph warns about. It has not fired yet because no launcher
currently in this tree uses a two-token interpreter flag (`grep` across `src/` turns up only
`-u`, `-m`, `-c`, all single-token or already special-cased) — but the module's own docstring
treats `-X` as a member of the same "interpreter flag, keep looking" family as `-u`/`-O` at line
18 and in the comment at line 55, and it is not one: it is the one flag on that list whose common
usage takes an argument. The module claims to protect against this whole class of false
negative and has an unhandled instance of it sitting inside its own stated defenses.

**Confidence:** Read the parsing logic, then reproduced the false negative directly against the
real `overnight._cmd_tokens`/`whoruns.script_of` in the project's own interpreter (shown above).
Confirmed by grep that no current launcher in `src/` triggers it today, so the live jobs this
tree runs are not currently affected — this is a latent gap in a brand-new safety tool, not an
active incident.

### MAJOR — `running()` never applies `overnight`'s own tree-scoping check, so it can report a sandboxed mutation-testing copy as the real script running

**Where:** src/whoruns.py:62-89 (`running`), contrast with src/overnight.py:244-254
(`running`'s call to `_in_this_tree`) and src/overnight.py:296-334 (`_in_this_tree` itself)

**What:** `whoruns.running()` matches a candidate process purely on
`os.path.basename(script) == want` (line 87) once `script_of` has named a script. It never asks
whether that script is *this checkout's own copy* of the file. `overnight.running()` — solving
the identically-shaped problem for the identical reason — reads (overnight.py:246-254):

> "AND IT MUST BE THIS TREE'S COPY. `mutate.py` runs the whole battery inside a SANDBOX -- a
> throwaway temp copy of `src/` -- so a sandboxed `python src/verify_math.py` has a command line
> indistinguishable from the live one and differs only in its cwd. Matching on the name alone
> made the battery's own answer depend on whether a mutation run happened to have a child alive
> ... `codewatch.twins()` was fixed for exactly this earlier in run #34, after the same confusion
> HALTED the library."

and applies `_in_this_tree(pid, cmd)` before returning `True`. `whoruns.running()` has no
equivalent call anywhere in its body.

Confirmed `mutate.py` does in fact copy `src/` into a throwaway sandbox root and run the battery
scripts from inside it under their ordinary basenames (`src/mutate.py:51-52`: "`src/` is copied,
`data/` `prompts/` `reference/` are junctioned..."), so a live process during a mutation run has
a command line like `python <sandbox_root>/src/verify_math.py`, whose basename is
`verify_math.py` — indistinguishable from the real thing to `whoruns.py`'s matching logic.

**Why it is wrong:** While a mutation-testing battery is running (a routine, scheduled activity
in this project), `python src/whoruns.py verify_math.py` (or any other battery member) will
report the sandbox's throwaway copy as `1 process(es) RUNNING verify_math.py`, indistinguishable
from the genuine article. `whoruns.py`'s own docstring frames its entire purpose as replacing
exactly this kind of unreliable ad hoc check with a trustworthy one ("the correct version is not
a one-liner"), and cites `codewatch.twins()`'s sandbox-confusion bug (run #34) as a named,
already-fixed instance of this same failure shape one module over. `whoruns.py` reproduces the
pre-fix behaviour rather than the fix. It is not exercised by today's only caller
(`drill.py`'s self-test uses fixed strings, not the live process table, and never runs during a
mutation battery), so nothing is currently misreporting — but the moment an operator or a future
script reaches for `whoruns.py` during (or racing) a mutation run, which is exactly the situation
its own docstring says four maintenance runs got wrong by hand, it will give the same wrong,
confident answer.

**Confidence:** Read `whoruns.running()` end to end and confirmed no call to `_in_this_tree` or
any cwd/path check exists in it. Read `overnight.running()` and `overnight._in_this_tree()` in
full for the contrast. Confirmed via `mutate.py`'s own docstring and `_junction`/sandbox-building
code that the sandboxed battery does run same-named `.py` files from a copied `src/` tree. Did
not spin up an actual mutation run to observe the false positive live (that would mean running
`mutate.py`, out of scope for a read-only audit), so the triggering scenario is confirmed by
source inspection and the module's own documented sandbox behaviour, not by reproduction.

Nothing else found in `whoruns.py`. The tri-state `running()` (None/[]/[hits]) contract, the
`--quiet` exit-code semantics (0 = found, matching grep, with the direction called out
explicitly), and the None-vs-empty-list handling of `overnight._proc_lines()`'s return value were
all checked against `overnight.py`'s source and are correct.

---

## escalation.py

Read in full (1445 lines). This file already carries an extremely dense history of prior
sweep-found bugs (documented inline by order number), so most of my time went to checking that
the described fixes actually match the code as it stands, and to a fresh look at the parts of
`escalate()`'s bad-level handling, the CAS loops (`_raise_halt`/`_land_halt`/`clear`/
`_write_stopped`/`resume_subsystem_verdict`), and `_by_a_person_at_the_cli`'s frame-depth
arithmetic.

Traced: the bad-level coercion chain in `escalate()` (string name -> float non-integer -> int()
failure -> range check, each landing at MANAGER with the bad value preserved in evidence) for
several inputs (`"OWNER"`, `"Owner "`, `2.7`, `3.0`, `None`, out-of-range ints, `True`) and it
resolves each one the way the surrounding comments claim. Traced `_by_a_person_at_the_cli`'s
`sys._getframe(2)` arithmetic for both its callers (`clear()` and `resume_subsystem_verdict()`
via `main()`) and the frame indexing is correct for both call shapes. Checked `_land_halt`'s
CAS-under-lock loop and `_halt_file_records`'s identity check (`(code, at)` tuple, checked against
both the standing halt and every `also` entry) for a lost-update window and found none: the digest
is taken before every re-read, as documented.

No new findings. Clean, with the above checked.

---

## codewatch.py

Read in full (953 lines). Checked `stale()`'s dual-clock settle logic (`seen` vs `quiet`, and the
"corroborated against the stamp" fallback when `quiet_seconds()` predates process start) by
tracing through several timelines by hand; checked `_take_locked`/`_claim_restart_slot`'s
enforce/used-before contract against `exit_if_stale`'s "spent vs ledger-denied" disambiguation
(confirmed the write-denied branch can only be reached when `used_before < BUDGET_PER_HOUR`, so
the two causes are never confused); checked `coverage()`'s roster union logic in `main()` against
the two different naming conventions (`overnight.ALL_JOBS`'s `"foo.py --flag"` fragments vs the
ledger's `stamp()`-supplied bare `who` strings) and confirmed the `.py` suffix stripping actually
normalises them to the same keys.

No new findings. Clean, with the above checked.

---

## endpoint.py

Read in full (578 lines). Checked the `_save()`/`register()` compare-and-swap merge logic (digest
taken before read, dirty-set difference_update only after a landed write, re-fold of the merged
file back into `_MEM` excluding anything dirtied mid-save) and it is internally consistent.
Checked `detect()`'s DEAD_TTL re-probe gate and the ordering guarantee at the bottom of the file
(the `if __name__ == "__main__":` guard is deliberately last, per its own comment, and I confirmed
`MODE_HTML`, `html_text`, `fetch_html`, `source_pages`, `register` are all defined above it in
file order, so `main()` can actually see them when run as a script).

No new findings. Clean, with the above checked.

---

## tiers.py

Read in full (544 lines). Verified the math behind the containment claim printed by `main()`
("sources whose lower group is split across two higher ones") rather than taking it on faith: the
multiverse tier is built by `weave.components()` (complete-linkage clique agglomeration — every
pair inside a cluster is checked pairwise against `MULTIVERSE_THRESHOLD`), and the metaverse tier
by this file's own `_components()` (single-linkage BFS at the strictly lower `CUTS[0][1]=100.0`
threshold) over the *same* weight dict `w`. Since every pairwise edge inside a multiverse clique
is `>= 102.3 >= 100`, every such pair is also directly adjacent in the metaverse graph, so two
sources sharing a multiverse cannot land in different metaverses — the containment the scan checks
for is actually guaranteed by construction for that pair, independent of the scan's
`if c["xenoverse"] is None: continue` gate (which restricts the loop to sources that also have a
xenoverse). I traced this to rule out a suspicion that the gate silently narrows the "invariant
reaches the write" check to a subset of the corpus; it does narrow the loop's *iteration set*, but
not in a way that can hide a real violation, because the multiverse/metaverse containment cannot
be violated given how both tiers are built from the same graph. Reported here as a checked-and-
cleared line of investigation, not a finding, per the brief's instruction not to file what
verification did not confirm.

No new findings. Clean, with the above checked.

---

## sevenfold.py

Read in full (442 lines). Checked `_even_cuts`'s boundary clamping, `seams()`'s
window-plus-median-eligibility logic against the three measured shapes its own comment compares
(global-weakest / window-only / window-plus-median), and `build()`'s two-population accounting
(`coords` from the resonance graph vs `by_source` from `worldseed.build_all()`, with the
`UNSHELVED` dict as the documented seam between them).

No new findings. Clean, with the above checked.

---

## resync_roll.py

Read in full (333 lines). Checked the duplicate-source bookkeeping (`dupes.setdefault` racing
against the unconditional `by_source[key] = (rec, fn)` overwrite) for an off-by-one in which
duplicate is recorded as the prior "winner" and traced it correctly picks up whichever file was
the current winner at the moment the next duplicate was found. Checked the `--dry-run` guard
(argparse rather than a substring test on `sys.argv`, per the file's own fixed-bug note) and the
exclusion-guard re-check inside `_apply()` (`r.get("status") != _roll.OUT_OF_SCOPE`, a bare `!=`
rather than folded into a compound condition, matching the comment's claim about what the drill
net can parse).

No new findings. Clean, with the above checked.

---

## cosmology_graph.py

Read in full (261 lines). Checked the inverse-document-frequency weight formula against the
module docstring's worked numbers (`1/log(n+1.5)`, `x0.15` above `UBIQUITOUS_CUTOFF`) by hand for
n=2 and n=3, matching the 0.80/0.68 figures quoted. Checked that `--write`'s JSON emits the whole
`pairs` list unfiltered (`ranked`, built from all of `pair_w`, with no threshold applied before
the list comprehension) and that `threshold` is only ever passed to `components()`, matching the
"pairs_filtered": False / "threshold_applies_to": "clusters" fields the file writes about itself.

No new findings. Clean, with the above checked.

---

## local_agent.py

Read in full (1639 lines) — the largest module in the batch, and the one with the most write
authority (it is the only lane that lets a model patch `src/` directly). This file also carries
an extremely dense inline history of eight-plus previously-found gate bypasses (case folding, ADS
streams, junctions, hard links, case-sensitive extension tests, the import-gate-checking-the-
wrong-file bug, the `None`-vs-`""` `why` crash, the empty-find bypass). I re-derived each of the
described fixes against the current code rather than trusting the comment, specifically:

- `_safe()`'s three-stage path resolution (component-level colon/trailing-dot-or-space refusal,
  prefix-vs-directory-boundary fix, realpath-based junction detection comparing written vs
  resolved relative spellings) — traced by hand for a `src/foreman.py::$DATA` ADS path, a
  `..-EVIL` sibling-prefix path, and a `handoff/link -> state/` junction scenario; all three are
  correctly refused by the code as it stands today.
- `_protected_identities()`/`_identity_denied()`'s hard-link defense — confirmed it is keyed on
  `(st_dev, st_ino)` and skips `st_ino == 0` rather than colliding every such file at `(dev, 0)`.
- `_gates()`'s per-file-type dispatch and the `modname`/`_in_src` import-gate fix — confirmed the
  by-path `importlib.util.spec_from_file_location` branch is only taken outside `src/`, and the
  by-name `import <modname>` branch (the real import path) is kept for files inside `src/`.
- `t_propose_patch`'s ordering of denylist -> allowlist (both path spellings) -> region denylist
  -> uniqueness check -> blast-radius charge -> write -> gate -> revert-on-failure, and the
  "empty find string" refusal ahead of the uniqueness count (`str.count("")` would otherwise
  return 1 against a zero-byte file).
- `_blast_ok()`'s charge-then-check ordering against `MAX_PATCHES_PER_RUN`/`MAX_FILES_PER_RUN`
  (confirmed exactly `MAX_PATCHES_PER_RUN` patches and `MAX_FILES_PER_RUN` distinct files are
  permitted before the next one is refused, not off by one in either direction).
- `_achievement()`'s four false-success guards (empty attempted+empty answer, attempted-but-
  unpaged, zero tool calls, attempted-and-none-landed) against the four incident write-ups in its
  own docstring.
- `_tool_message()`'s envelope-vs-payload truncation fix (confirmed the shrink loop always
  reserializes and re-measures rather than computing a byte budget once, and that `slice`'s
  companion `chars_after_slice` is recomputed from the *shortened* slice rather than left
  describing the original).

No new findings. Clean, with the above checked.
