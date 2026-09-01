# Sweep 40 — Batch 06 audit

Modules: `src/feats.py` (1,866 lines), `src/derivation.py` (743), `src/manifest_builder.py`
(592), `src/address_space.py` (486), `src/thread_integrity.py` (392), `src/hosts.py` (315),
`src/scope.py` (275), `src/scale_theories.py` (174), `src/repass_bands.py` (149). All nine
read in full (`cat -n`, sequential windows for the larger files — no sampling), per Hard
Rule 0.

## Context

Like the other modules in this tree, all nine are heavily self-audited: most already carry
long comments documenting a prior real defect (tautology, fail-open, discarded write verdict,
Hard-Rule-0 truncation, read-modify-write race) and its fix, frequently citing an order id or
a `run #N` sweep. `derivation.py`'s own graph-integrity checker was re-run directly
(`check_graph()` → 0 problems against the live ledger) to confirm its claims hold today rather
than trusting the prose. Given that density of prior correction, this pass concentrated on:
places where a caller discards a function's return value even though the function's own
docstring says the return value is the thing a caller must check; comments that assert
something about the code sitting two lines below them that the code does not do; and the
read-modify-write / locking discipline around every module-level mutable dict.

Two real, previously-unflagged findings came out of that. Everything else read as either
already correct or already-fixed-and-documented; those are not re-litigated below except
where noted.

## Findings

### 1. `feats.py --roll` always exits 0, even when the roll did nothing or errored throughout (MAJOR)

**Where:** `src/feats.py:1838-1842`, the `--roll` branch of `main()`:

```python
1838	    if a.roll:
1839	        recs = P.records()
1840	        hosts = resolve_hosts(recs, verify=False)
1841	        roll(recs, hosts, workers=a.workers, limit=a.limit, only=a.only)
1842	        return 0
```

**The problem.** `roll()` (`src/feats.py:1785-1866`, def at 1786) builds and returns a `done`
dict (`return done` at line 1866) that carries exactly the counters this file's own doctrine
insists must be surfaced: `n` (jobs attempted), `errored` (entities whose `evidence_for()`
raised), `empty` (entities with no page), `feats`/`quant` mined, etc. The `--roll` branch of
`main()` calls `roll(...)` and throws the return value away — no assignment, no check — and
then unconditionally `return 0`.

This means:

* If `resolve_hosts(recs, verify=False)` at line 1840 returns an empty or near-empty host map
  (e.g. because `WIKI_HOSTS.json` is momentarily unreadable, or every source is filtered out),
  `jobs` inside `roll()` is `[]`, `roll()` prints `roll: 0 entities across 0 wikis, 8 workers`,
  mines nothing, and `main()` still returns 0.
* If every single entity's `evidence_for()` call raises (a systemic bug — e.g. a bad import, a
  broken cache path, `endpoint.py` failing for every host), `done["errored"] == done["n"]`,
  `done["feats"] == 0`, and `main()` still returns 0. The printed summary line
  (`f"{done['errored']:,} entities that raised"`) says so on stdout, but the process exit code
  — the one channel this codebase's own `run()`/`join()` supervisor machinery in
  `src/overnight.py` actually inspects — reports success regardless.
* `resolve_hosts()`'s own docstring (`src/feats.py:832-834`) explicitly promises: *"The
  returned map is the in-memory one and is correct whether or not the cache write landed;
  `_HOSTS_DENIED` says which, and `main()` exits nonzero on it."* That promise is honoured by
  the sibling `--hosts` branch (`src/feats.py:1825-1836`, which checks `_HOSTS_DENIED` and
  `return 1 if _HOSTS_DENIED else 0`) but **not** by the `--roll` branch: `resolve_hosts()` is
  called at line 1840 and neither `_HOSTS_DENIED` nor the map's completeness is inspected
  before `roll()` runs and before `main()` returns 0.

**Why it matters, concretely.** `src/overnight.py:1414` launches this exact invocation as a
long-lived backgrounded job (`start("roll", [..., "feats.py", "--roll", "--workers", "12"],
LN.ROLL)`), and `src/overnight.py:1414+` (`join(roll, timeout_h=4)`) is the one place the
supervisor learns whether it went well:

```python
# src/overnight.py:638-662 (join())
job["proc"].wait(timeout=timeout_h * 3600)
rc = job["proc"].returncode
log(f"  {job['name']}: finished {name_rc(rc)} in {(time.time()-job['t0'])/60:.0f}m")
if rc != 0:
    tail(os.path.join(STATE, os.path.basename(job["fh"].name)), job["name"])
return "ok" if rc == 0 else f"rc={rc}"
```

`join()` only tails the roll's log and reports anything other than `"ok"` when `rc != 0`. A
roll that mined nothing, or that errored on every entity, produces `rc == 0` and is reported
as `"ok"` in the same words as a roll that mined tens of thousands of feats — exactly the
"exit code reports success for a run that did nothing" shape this sweep is looking for, and
the same failure class this file's own comments elsewhere describe fixing for `--hosts`
(`_HOSTS_DENIED` → `return 1`), for `scope.py --build` (`return 1` on a denied write), and for
`repass_bands.py` (`return 1` when any record write is denied). `--roll` is the one CLI branch
in this file where the pattern was never applied, even though the function it calls hands back
exactly the counters needed to do it.

**Remedy.** Capture `roll()`'s return value and fold it, and `_HOSTS_DENIED`, into the exit
code, e.g.:

```python
if a.roll:
    recs = P.records()
    hosts = resolve_hosts(recs, verify=False)
    done = roll(recs, hosts, workers=a.workers, limit=a.limit, only=a.only)
    if not done["n"]:
        print("ROLL DID NOTHING: 0 jobs (check WIKI_HOSTS.json / --only)")
        return 1
    if done["errored"] == done["n"]:
        print(f"ROLL FAILED: all {done['n']:,} entities raised")
        return 1
    return 0
```
(exact thresholds are a judgment call for whoever picks this up — the point is that some
signal from `done`/`_HOSTS_DENIED` should reach the exit code, as it already does for every
other write/verdict-bearing branch in this file).

---

### 2. Stale, self-contradicting comment above `FIELDS` in `address_space.py` (MINOR)

**Where:** `src/address_space.py:148-153`:

```python
148	# hyperverse and xenoverse are NOT fields. They are not unknown values awaiting a survey -- they
149	# are positions the charter declines to state, and reserving bits for them would invite filling
150	# them in.
151	FIELDS = [
152	    ("hyperverse", max(2, _TC["hyperverse"])),
153	    ("xenoverse",  max(2, _TC["xenoverse"])),
```

**The problem.** The comment asserts, in the present tense, that hyperverse and xenoverse
"are NOT fields" and that bits are deliberately *not* reserved for them ("reserving bits for
them would invite filling them in"). The code two lines below does exactly what the comment
says is being avoided: `FIELDS` puts `"hyperverse"` and `"xenoverse"` in first, with real
computed widths (`WIDTHS[name] = _bits(n)` for both, contributing to `TOTAL_BITS`), and
`assign()` (`src/address_space.py:360-361`) explicitly fills them in from the source's charted
tier stack:

```python
360	    return pack(fit(tiers.get("hyperverse"), "hyperverse"),
361	                fit(tiers.get("xenoverse"), "xenoverse"),
```

The sibling `shelfmark()` docstring two hundred lines below (`src/address_space.py:191-206`)
confirms this is deliberate current behaviour, and even narrates the exact confusion this
stale comment now perpetuates: *"THIS DOCSTRING SAID THE OPPOSITE FOR THREE SWEEPS. It claimed
H and X print as '?' -- true of Part Two, and true of this function until tiers.py charted the
upper tiers... The behaviour is deliberate and stays; only the description was wrong."*
`shelfmark()`'s own docstring was corrected for this drift; the comment directly above
`FIELDS` — describing the exact same design point one layer lower, where the bits are actually
allocated — was not, and now reads as the exact belief `shelfmark()`'s docstring says is wrong
("Hyperverse position is uncharted... the Custodes considered guessing a form of lying").

This is very likely a genuine leftover from the pre-`tiers.py` design (when hyperverse/
xenoverse genuinely were not addressable and always printed `?`), left in place across the
same refactor that `shelfmark()`'s docstring documents fixing everywhere else in this file.

**Why it matters.** It is not a live functional bug — `FIELDS`, `WIDTHS`, `pack`/`unpack`, and
`assign()` are all internally consistent and `verify_math`'s exercised round trip
(`address_space.py:404-414`) passes. The risk is exactly the one this codebase's own doctrine
warns about repeatedly elsewhere ("a check that cannot fail looks exactly like a check that
passed" / stale docs): a future maintainer reading this comment in isolation — directly above
the code it is describing, unlike the far-away `shelfmark()` docstring — could "restore" the
described behaviour (e.g. by excluding hyperverse/xenoverse from `FIELDS` again, or by masking
them to 0 in `assign()`), which would be a real regression, re-introducing the exact `?`-guess
problem `tiers.py` was written to remove, on the authority of a comment that no longer matches
the module's own stated design.

**Remedy.** Delete or rewrite lines 148-150 to match current behaviour — e.g. note that
hyperverse/xenoverse *are* ordinary fields since `tiers.py` charted them, cross-referencing
`shelfmark()`'s docstring rather than contradicting it.

## Other observations (not filed — deliberate design or already fixed)

* `feats.py`'s `mine()` (`src/feats.py:1178-1213`) only stores a sentence in `gate_rejected`
  when it also matches `_QUANTITY` or a destroy/obliterate/shatter/survive keyword; a sentence
  that fails `valid_scale_note` and matches neither is dropped without a trace. The module
  docstring's "it keeps everything it gathers, including what the gate turned down" reads as a
  stronger promise than the code delivers. Given `pipeline.valid_scale_note` passes only 0.28%
  of wiki sentences (documented at `src/feats.py:1216`), keeping literally every rejected
  sentence would balloon every cache file to near-corpus size; the current filter looks like a
  deliberate curation of near-miss candidates rather than an oversight, and `gate_rejected` is
  not consumed anywhere as a computed "rejection rate" today. Filed here as a question, not a
  finding — worth an owner call on whether the docstring should be narrowed to match.
* The `handoff/sweep24/AUDIT_batch06.md:320` citation inside `scope.py:98` was checked against
  that file's actual line 320 and matches (the old `srlimit=3`/`titles[:8]` finding it
  describes is real and is what the surrounding code in `scope.py` now fixes). Not stale.
* Cross-file citations `liveness.py:89-103`, `read.py:80`, `pipeline.py:2024`,
  `standards.py:1009`, and `catalogue_codex.py:315-331` (from `derivation.py`,
  `manifest_builder.py`, `address_space.py` x2, and `scope.py` respectively) were all spot
  checked against current source; each points at the region of code it claims to. Not stale.
* `derivation.py`'s `check_graph()` was re-run directly against the live `LEDGER` and returns
  zero problems, confirming the module's own "graph closes" claim rather than assuming it.
* `hosts.py`'s `discover()` calls `add()` (the SOURCE_HOSTS.json read-modify-write) only from
  the single consuming thread of `for res in ex.map(work, todo): ...` — the `ThreadPoolExecutor`
  parallelism is confined to the read-only `work()` probes, so there is no concurrent
  read-modify-write on `SOURCE_HOSTS.json` despite the multi-worker discovery walk. Checked
  specifically because the shape (multi-worker discovery + a shared JSON registry) is exactly
  where this codebase has had races before; this one does not have one.
* `thread_integrity.py`'s exit code (`return 1 if dangling else 0`) deliberately does not grade
  on `PARTIALLY-DANGLING` or `IMPLIED-UNRECORDED` — the surrounding comment cites
  `STEP4_PLAN.md §8` ("DANGLING = 0 is a release gate, not a metric") as the authority for that
  scoping. Read as deliberate, not a finding.
