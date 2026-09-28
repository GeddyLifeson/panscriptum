# sweep66 batch14 — audit report

## Scope

Every module read in full, start to finish, sequentially, via the Read tool in chunks (large
files split into two reads with no gap between offsets), no sampling and no grep-driven skimming.
Line counts from `wc -l` at time of reading:

| module               | lines |
|----------------------|------:|
| src/hostcheck.py      | 1735  |
| src/health.py         | 1319  |
| src/liveness.py       | 1089  |
| src/secondopinion.py  |  712  |
| src/anchors.py        |  576  |
| src/coverage.py       |  456  |
| src/sweep.py          |  374  |
| src/roll.py           |  313  |

Total 6,574 lines across 8 modules, all read completely.

READ-ONLY throughout: nothing under `src/`, `data/`, `state/`, `output/`, `prompts/`, `reference/`
or the repo root was edited or created, other than this file and the `sweep_plan.record()` call at
the end. No generator, pipeline, publish, crawl, `overnight.py`, `foreman.py`, `mutate.py`,
`drill.py` or `verify_math.py` was run. No `escalation` halt or `prose_enabled`/`step4_enabled`
gate was touched. No subagent was spawned. One data-only, read-only check was run outside the
batch (a `python -c` one-liner reading `data/SWEEP_ROLL.json` and `data/WIKI_HOSTS.json` to see
whether a code-level suspicion about `hostcheck.py` had a live example on the actual roll; no
network call was made and nothing was written).

## Prior-audit cross-check

This batch is identical to `handoff/sweep65/AUDIT_batch14.md`'s batch except one module:
`secondopinion.py` replaces `weave.py`. `sweep65/AUDIT_batch04.md` covered `secondopinion.py`
under a different grouping.

- **sweep65/AUDIT_batch14.md** (hostcheck, health, liveness, weave, anchors, coverage, sweep,
  roll): 0 VERIFIED, 0 SUSPECTED findings. One QUESTION carried forward (`liveness.py`'s
  `DECLARED_UNREACHABLE` lookup silently excusing nothing when a declared function name matches no
  def at all — still true of the current source, re-traced this pass at `liveness.py:984-990`,
  unchanged; still a QUESTION not a finding, fails in the safe direction).
- **sweep65/AUDIT_batch04.md** (secondopinion, among seven others): 0 VERIFIED, 0 SUSPECTED
  findings against `secondopinion.py`; confirmed `ran_clean()` cannot be vacuously true because
  `run()` always populates all three tool entries.
- Earlier sweeps (sweep63, sweep64) cited by sweep65's own cross-check also carry zero findings
  against these eight modules under earlier groupings (sweep64 batch14, batch12, batch13/04;
  sweep63 batch08/09 for roll.py).

So every module in this batch has a clean multi-sweep history at this point. This pass re-traced
the logic by hand rather than trusting that history, and found two items the prior passes did not
name (below) plus reconfirmed the open work orders already covering parts of this batch.

`state/workorders.json` (1,108 lines) was searched for each module's filename and for the specific
symbols this pass's own findings touch (`relevance`, `_tokens`, `about_n`, `flush_samples`,
`SAMPLES_PATH`) before writing anything down:

- **`a8e02f3bbf76`** (`HOSTCHECK_EXAMPLES_PERSISTED_CAP`) — `hostcheck.probe()`'s `examples` field
  is still `sorted(got)[:5]` (RAW branch, line 418) and `found = [...][:5]` (API branch, line 441),
  while `titles` carries the uncapped list and the verdict itself is computed over the whole list.
  Confirmed still accurate against current source. Already OWNER-routed (order text explicitly
  also flags `relevance()`'s own 12-title read and the 40/12-name roster probes as the same class
  of question, not yet separately filed). Not re-filed.
- **`21c075e5e2d6`** / **`3099138a82bd`** (writers without a halt interlock — the class question
  routed to the owner) — `21c075e5e2d6` names `health.py --reopen --go` by symbol (batch14) as a
  writer of `PIPELINE_STATE.json` that never calls `escalation.assert_clear()`; `3099138a82bd`
  names `src/roll.py` by symbol (batch14) the same way for its `mutate()`/`exclude()` writers of
  `SWEEP_ROLL.json`. Both confirmed unchanged against current source (grep for `escalation` in
  `health.py` and `roll.py` finds no import, no call — see body). Not re-filed; this is the
  question already on file, not contradicted by a fresh read.
- **dandwiki headline sentence** — the OWNER-routed order attached to `health.check_api_paths`
  records that "probed host did not answer" is literally false for `www.dandwiki.com` (it answers
  403, not silence) and asks whoever rules on the 403-by-policy question to fix the sentence at
  the same time. Confirmed still present, now at `health.py:727` (line drift from the order's
  `:726`, expected — line citations in this tree rot weekly, per the order's own text). Not
  re-filed.
- No open order matches this pass's two new findings below (`_flush_samples`'s silent
  double-failure swallow; `relevance()`'s ambiguous `(None, 0)` sentinel) by module, symbol, or
  keyword.

## Findings

### DEFECT 1 — `health.py`'s `_flush_samples()` silently drops a real fault its own sibling function reports

**Where:** `src/health.py:462-463` and `:508-509`.

**The code (abbreviated to the load-bearing lines):**
```python
def _flush_samples(taken_s):
    try:
        for _attempt in range(FLUSH_CAS_ATTEMPTS):
            ...
            if os.path.exists(SAMPLES_PATH):
                try:
                    with open(SAMPLES_PATH, encoding="utf-8") as f:
                        old = json.load(f)
                    if not isinstance(old, dict):
                        raise ValueError(...)
                except Exception as e:
                    if not silence.replace_retry(SAMPLES_PATH, SAMPLES_PATH + ".corrupt"):
                        raise                                    # <-- (A)
                    old = {}
                    ...
                    print(f"health: failure samples unreadable ...", file=sys.stderr)
            ...
        silence.note("health.py:samples-write-lost")
    except Exception:
        pass          # the evidence bag must never break the ledger write   # <-- (B)
```

**Why it is wrong.** When `SAMPLES_PATH` is torn or wrong-shaped *and* the rename-aside to
`SAMPLES.json.corrupt` is itself denied (line (A): the exact WinError-5 "a reader holds the file
open" case this whole file's doctrine is built around), the original exception is re-raised. It
is not caught anywhere inside the `for` loop — the `silence.note("health.py:samples-write-lost")`
line is only reached if the loop runs to exhaustion without an exception — so it propagates
straight to the outer `except Exception: pass` at (B). Nothing is printed, `silence.note` is never
called, and the function returns silently having recorded nothing about what happened. `_SAMPLES`
(the in-memory ring) is untouched, so the data is not lost *this call*, but if this is the flush
`atexit` fires (health.py registers `flush()` there via `silence.note`'s instrumenter), the
process exits immediately afterward and the samples are gone with literally no trace anywhere —
not in `state/failures.json`, not on stderr, not via `silence.note`.

Compare the *identical* scenario in `_flush_ledger()`, twenty-odd lines earlier in the same file
(`health.py:350-355`): when the same double failure occurs (unreadable ledger, preserve-rename
also denied), that function explicitly does
```python
print(f"health: ledger unreadable ({type(e).__name__}) AND could not be set "
      f"aside as {_wreck} (rename refused) -- refusing to write "
      f"over it; counts kept in memory for the next flush", file=sys.stderr)
return
```
— a stated reason, on stderr, and a clean `return` rather than a re-raise into a blanket handler.
`_flush_samples`'s inline comment at the `raise` even says "the original exception is re-raised
into the blanket `except` below and this flush drops its samples exactly as it did before. That
is the old behaviour and it is the safe one" — which defends *not overwriting the wreck* (correct,
and the right call), but never addresses that the drop itself goes unrecorded, unlike its sibling.

This is precisely the shape this module's own docstring names as the project's standing failure:
"Every layer converts a failure into a plausible NEGATIVE RESULT. Nothing raises, nothing counts."
A prior audit (`handoff/sweep56/AUDIT_batch14.md:119`) explicitly examined this area and concluded
"No bare `except: pass` that swallows a real fault silently — every blanket except block found
either calls `silence.note(...)` or is explicitly justified inline." That conclusion does not hold
for this specific branch: the justification given is about data safety, not about the silence,
and no `silence.note` call is reached on this path.

**Verified how:** by direct control-flow trace (not execution) — read every line of
`_flush_samples`, confirmed the `raise` at (A) has no enclosing handler until the outer `try` at
line 424, and compared line-for-line against `_flush_ledger`'s handling of the same fault shape.
No standalone reproduction was run (this is a pure control-flow argument, and reproducing the
double failure would require denying a rename on a live shared state file, which is out of scope
for a read-only audit). Confidence is high because the divergence from the sibling function is
structural, not a matter of interpretation.

**Concrete failure scenario:** `state/failure_samples.json` becomes torn (a kill mid-write, or a
concurrent writer's half-finished rename — this project's own history records exactly this class
of event on this file's sibling, `state/failures.json`, more than once) at the same moment another
process holds the file open for reading (the dashboard, or a competing flush), so
`silence.replace_retry` cannot rename it aside. The next `--failures`-adjacent flush (including
the final one at process exit) silently discards the evidence bag with zero record anywhere that
it happened, and the failure this module exists to make loud is, in this one path, the quietest
thing in the file.

**Remedy shape** (not applied — read-only audit): give `_flush_samples`'s double-failure branch
the same treatment `_flush_ledger`'s already has — a `silence.note(...)` call and a stderr message
before returning, rather than an uncaught `raise` into the terminal `pass`.

### DEFECT 2 (lower confidence) — `hostcheck.py`'s aboutness veto misreports its own cause for a short/stopword-only source name

**Where:** `src/hostcheck.py:511-537` (`relevance()`) and `:938-967` (`score()`'s consumption of
its `(None, 0)` return).

**The code:**
```python
def relevance(host, titles, source, sample=12):
    titles = [t for t in titles if t][:sample]
    toks = _tokens(source)
    if not titles or not toks:
        return None, 0
    ...
```
and, in `score()`:
```python
elif r["about"] is None and r["about_n"] == 0:
    ...
    r["verdict"] = ("UNREACHABLE — no article body could be read, so aboutness could not "
                    "be measured")
```

**Why it is wrong.** `relevance()` returns the identical sentinel `(None, 0)` for two different
causes: (a) `_bodies()` genuinely could not fetch any article text (a throttle, a 403, a network
fault — the case the verdict message describes), and (b) `_tokens(source)` is empty, so no
distinctive word exists to test article bodies against *and no fetch is even attempted* — this
branch returns before `_bodies()` is ever called. `_tokens()` (`hostcheck.py:478-488`) requires
`len(w) > 2`, so any source whose name is entirely two-letter words and/or stop-words produces an
empty token list. `score()`'s verdict text for this sentinel unconditionally claims "no article
body could be read," which is the wrong reason for cause (b): nothing failed to be read; nothing
was ever asked, because the source name itself gave the function nothing to search for.

**Verified how — partially.** The code path was traced by hand (VERIFIED as a real, reachable
branch: `_tokens("DC")` returns `[]` since `"dc"` is only 2 characters). A read-only check of
`data/SWEEP_ROLL.json` (215 sources) found exactly one live source name that produces an empty
token list this way: **`DC`**. Checked against `data/WIKI_HOSTS.json`, `DC`'s assigned host is
`dc.fandom.com`. `relevance()` is only ever called from `score()` when `r["hits"] and base is not
None and base >= ABOUT_VETO_ABOVE` (0.25) — i.e., only against a "generous" host — and this
module's own docstring table states `dc.fandom.com` answers only ~5% of foreign names, well under
that 0.25 veto threshold, so on `DC`'s *own* host the veto (and therefore `relevance()`) is not
currently invoked; `data/HOST_FITNESS.json`'s stored `DC` row (`about: None`, no `about_n` key,
`baseline: null`) is from a version of this module that predates the current `score()` logic
entirely (it shows `verdict: "holds"` with `baseline: None`, which the current code cannot
produce — `base is None` now always yields `UNREACHABLE` — so it is stale data, not evidence of
today's behaviour). This module's own `candidates()`/`candidates_split()` always add
`en.wikipedia.org` as a repair/adopt candidate (a generous host, ~50% per the docstring table), so
the branch would fire if `DC` were ever re-probed against Wikipedia during `sweep(--repair)` or
`adopt()` — but no network probe was run to confirm this live (prohibited for a read-only audit
with no network access), so this is reported as a **SUSPICION**, not a fully verified live defect:
the code path is real and reachable in principle, and one live example of the triggering source
name exists on the roll, but it was not observed to actually fire against the current host map.

**Concrete failure scenario (hypothetical, code-verified, data-unconfirmed):** if `DC`'s host ever
needs re-evaluation and `en.wikipedia.org` is probed as a candidate with `hits > 0`, `score()`
would report `"UNREACHABLE — no article body could be read, so aboutness could not be measured"`
for a case where the true state is "the source's own name has no word long enough to search
article bodies for." An operator reading `HOST_FITNESS.json` would investigate a nonexistent
fetch failure rather than recognise the real, structurally different cause. The safe direction is
preserved (both readings return `UNREACHABLE`, never a false `holds`), so this is a diagnostic
accuracy defect, not a correctness/safety one.

## Questions (possible deliberate design — not findings)

1. **Carried forward from sweep63/64/65, unchanged** — `liveness.py:982-990`
   (`reachability()`'s `DECLARED_UNREACHABLE` handling). Re-traced this pass: if a name in
   `DECLARED_UNREACHABLE[module]` matches no def at all in `_function_line_ranges` (a typo, or a
   function since renamed/removed), the loop takes neither the `ambiguous` branch nor the `span`
   branch — it silently contributes nothing to `declared_lines`, so those lines reappear in
   `unreached_undeclared` as fresh gaps rather than the tool saying outright "declared function `X`
   not found." Fails in the safe direction (a stale ruling can only stop excusing something, never
   grant a false excuse). Still true of current source; still a candidate for an explicit "declared
   but not found" row if the owner wants staleness here as loud as elsewhere in this file.

No other design questions arose that were not already answered by these modules' own doctrine
comments or by the open orders listed above.

## Cleared (examined closely by hand, found correct)

- `hostcheck.py`: `score()`'s full verdict ladder including the mutual exclusivity of the
  about-veto's two UNREACHABLE branches; `null_rate`'s dedupe-then-stride sampling and its own
  `MIN_PROBE` floor on the control; `_land_hosts`'s compare-and-swap and absent-file refusal;
  `purge()`'s per-record-file accumulation (`n_entries` correctly summed across files, not
  overwritten by the last one); `candidates_split()`'s grounded/speculative split (Wikipedia and
  neighbours never truncated out).
- `health.py`: `_flush_ledger`'s compare-and-swap and preserve-the-wreck branch (this one *does*
  report the double-failure case correctly — the contrast with `_flush_samples` is finding 1
  above); `check_api_paths`'s registered-domain bucketing and quarantine exemption; `check_caches`'s
  triple exemption (quarantine / exclusion / 25-file floor) composing without one silently
  overriding another; `reopen_stranded`'s re-read-before-write compare-and-swap and its
  `None`-vs-`[]` contract.
- `liveness.py`: the receiver-aware DEAD pass (`_credit_attrs`/`_scope_aliases`) traced against the
  `drill.py` `R = roll` / `R = resonance` worked example by hand; the PHANTOM pass's widened test
  coverage; `reachability()`'s subprocess isolation from the project's own shadowing
  `src/coverage.py`.
- `secondopinion.py`: `ran_clean()` cannot be vacuously true; the fail-open-by-design absence
  handling (`NOT INSTALLED` vs `UNASKABLE`); `report()`'s tree-fingerprint torn-read guard.
- `anchors.py`: the `CLAIMS` table's five per-anchor tests re-traced against each anchor's actual
  `scores` dict; the graded invariants (finite interval, no unmechanised dispersion, positive bit
  value at every band, Lumen's vantage actually reaching the college).
- `coverage.py`: `state_of()`'s CITED > READ > NO PAGE > UNREACHABLE > NOT ATTEMPTED precedence,
  re-traced through every arrival order of candidate paths including the "READ always outranks a
  later NO PAGE, never the reverse" rule; `_CLASSIFIER_VERSION`'s wholesale cache-discard gate.
- `sweep.py`: `nested_run()` always returns a chain of length ≥ 1 (confirmed by trace: `best`
  starts at `(0,0)` but any `i` produces a run of at least length 1, which is `> 0`, so `best` is
  always overwritten at least once when `order` is non-empty).
- `roll.py`: `update_rows`'s `seen`-vs-`ch` fix (unconditional `seen.add` on a name match) still in
  place; `exclude()`'s compare-and-swap and required-note validation.

## Coverage recorded

Ran `sweep_plan.record('run66', ['hostcheck.py', 'health.py', 'liveness.py', 'secondopinion.py',
'anchors.py', 'coverage.py', 'sweep.py', 'roll.py'], batch=14)` from the kit directory via the
miniconda python, per the brief.
