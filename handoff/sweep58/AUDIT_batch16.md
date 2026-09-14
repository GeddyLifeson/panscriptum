# SWEEP 58 — BATCH 16 AUDIT

Agent: sweep58 batch 16 (read-only). Project: C:\Users\imarl\panscriptum-library-kit.
Modules read in full, top to bottom (no skimming, offset-paged where needed):

| module | lines |
|---|---|
| src/hostcheck.py | 1636 |
| src/binding_health.py | 1588 |
| src/scout.py | 833 |
| src/gpu_lane.py | 684 |
| src/anchors.py | 576 |
| src/pantheon.py | 432 |
| src/events.py | 339 |
| src/roll.py | 307 |

## Open queue checked first

Ran `workorders.open_orders()` against the live queue and filtered for anything touching this
batch's eight modules. Matches, each checked against the code as it stands now:

- **b6079a0d24bd** BINDING_HEALTH_RAW_MODE_PROBE_ALWAYS_READS_UNREACHABLE (`binding_health.py`
  `_probe_reachable`) — **KNOWN, NO LONGER ACCURATE.** This shift's fix is in and it is correct:
  a RAW-mode host is now probed with `EP.raw_url(host, "Main Page")` + `EP._get(url)` rather than
  falling through the API path (`F.api()` → `endpoint.api_url()` → `None` for RAW), and the three
  outcomes (True/False/None) are kept apart. `verdict()` was updated to match: `ok_reachable is
  None` is handled explicitly and separately from `False` in all three places it appears
  (lines ~1013-1020 and ~1031-1035), so an unmeasured RAW probe returns `(None, "not proven
  sound, not proven at fault")` rather than being folded into "host unreachable" and quarantined.
  Recommend closing this order.

- **c9146abf92df** ROLL_LOST_UPDATE_REMAINING_WRITERS (`roll.py:127 exclude()` half only;
  `foreman.py:189` is out of this batch and out of scope for this read) — **KNOWN, THE ROLL.PY
  HALF IS NOW FIXED.** `exclude()`'s no-`rows` path now runs entirely inside an `_apply` closure
  passed to `roll.mutate(_apply, path=ROLL)` (roll.py:265-285): the lookup, the "no such source"
  `ValueError`, and the no-change `_NoChange` short-circuit all run against the FRESH rows
  `mutate` re-reads on every compare-and-swap attempt, not a `load()`-then-blind-overwrite. I
  independently confirmed the companion claim that the `checks_L4.py` literal-string pin
  (order b3da16ddfe64) was restated as a property test rather than removed: it now writes a
  temp roll, calls `exclude()` on it, and asserts the non-ASCII text survives unescaped in the
  bytes on disk (`handoff/run35/checks_L4.py:112-132`) — a real property test, not a tautology.
  The `foreman.py:189` half remains open; not assessed here (out of batch, and `foreman.py` is
  owner-assigned elsewhere per the roll.py comment at line 253-261).

- **174c7948f15f** UNMARKED_DISPLAY_CUTS_SWEEP57 (`events.py:319,326` portion only; the
  `whoruns.py`/`cleanup.py` portions are out of this batch) — **KNOWN, THE EVENTS.PY PORTION IS
  NOW FIXED.** Line 320: `_h if len(_h) <= 58 else _h[:57] + chr(8230)`; line 328:
  `_sp if len(_sp) <= 46 else _sp[:45] + chr(8230)`. Both now carry the house ellipsis marker
  (`chr(8230)`) at the documented `s[:w-1] + ellipsis` shape, so a cut heading/span is
  distinguishable from a short one. `whoruns.py:154` and `cleanup.py:333,409-412` are unread
  this batch; do not close the order on their account.

- **30854f11f322** SWEEP35_FINDING (`binding_health.binding_verdict`, containment-only
  false-CONFIRMED at `token_set_ratio`==100) — **KNOWN, STILL ACCURATE.** Unchanged this shift.
  `binding_verdict()` (line ~888) still scores CONFIRMED at 100 whenever one name's words are a
  subset of the other's; the docstring now records `containment`/`tight` in the returned record
  so a reader can see when a CONFIRMED rests on containment alone, but the underlying
  classification is deliberately left as-is per the recorded owner reasoning (no metric
  separates the true containment cases from the false one without breaking the three live
  CONFIRMED calibrations). No action needed; correctly left open.

- **a8e02f3bbf76 / 5d0fa30e4b09 (item 9)** HOSTCHECK_EXAMPLES_PERSISTED_CAP — **KNOWN, STILL
  ACCURATE.** `hostcheck.probe()` still returns an uncapped `titles` alongside a 5-item
  `examples` (RAW branch `sorted(got)[:5]` at line 343-344; API branch `found = [...][:5]` at
  line 363-366), and `score()` still reads `r.get("titles")` for the aboutness pass and then
  `r.pop("titles", None)` (line 817) before the row reaches `HOST_FITNESS.json`, so only the
  5-item `examples` survives on disk. `hostcheck.py` is not in this shift's rewrite list; nothing
  changed here. The related note in the same order (probe samples 40/12 names, `relevance`
  reads 12 bodies) is also unchanged and remains a QUESTION, not a defect, per that order's own
  framing.

No open-queue hits for `gpu_lane.py`, `anchors.py`, or `pantheon.py`.

## Findings

### binding_health.py (1588 lines)

**DEFECT MAJOR** — `_probe_reachable`'s API-mode branch still folds "could not ask" into
"asked, and it said no," the exact fault this shift's own docstring says the RAW-mode arm two
lines above was rewritten to stop doing:

```python
    try:
        d = F.api(host, {"action": "query", "meta": "siteinfo"}, retries=0)
    except Exception as e:
        return False, "%s: %s" % (type(e).__name__, str(e))
```

Compare the RAW-mode arm immediately above it in the same function:

```python
        try:
            body = EP._get(url)
        except Exception as e:
            # NOT ASKED IS NOT ANSWERED -- same argument as `_probe_absent`'s own exception arm.
            # A timeout or a DNS failure on OUR side must not be read as a host fault.
            return None, "%s: %s -- could not ask (raw probe)" % (type(e).__name__, str(e))
```

`F.api(..., retries=0)` raising on a transient timeout, DNS blip, or connection reset for an
**API-mode** host returns `False` (a confirmed-dead verdict), not `None` (unmeasured) — the
opposite of what the RAW-mode arm two lines up, and `_probe_absent`'s own exception arm, and
this function's own docstring ("A request that cannot even complete (DNS, timeout, ...) is
reported `None` — UNMEASURED, not a verdict — rather than folded into the same False that means
'asked, and it said no'") all say must happen.

**Concrete failure scenario:** an API-mode host's `known_present_titles` candidates all fail
(any reason, including a run of transient fetch problems — `_probe_present` is only called with
`ok_p` falsy before `_probe_reachable` runs at all), `_probe_absent` correctly reports the
control clean (`ok_absent=True`), and then a single transient exception from
`F.api(host, {"action": "query", "meta": "siteinfo"}, retries=0)` (a timeout, a DNS hiccup, a
reset — `retries=0` removes any cushion) makes `_probe_reachable` return `(False, ...)`.
`verdict(False, True, False, ...)` falls through `if not ok_absent` (false), `if ok_reachable`
(false), `if ok_reachable is None` (false), to `return False, "host unreachable: ..."` —
`healthy=False`. `run()` then calls `quarantine(h, ...)` on a host that was never actually
demonstrated to be down — the same false-quarantine failure mode this whole module exists to
prevent (documented at length for the RAW-mode case at order b6079a0d24bd), left standing for
every API-mode host.

**Remedy:** mirror the RAW-mode arm — on an exception from the siteinfo call, return `None`
("could not ask"), not `False`, so `verdict()` routes it to the already-correct
`ok_reachable is None` branches instead of the hard-dead one.

**QUESTION** — `binding_health.py` has no call anywhere to `escalation.assert_clear` /
`_assert_not_halted`, unlike `hostcheck.py` (which gates every `WIKI_HOSTS.json`-repointing
write behind exactly this check, per order 77950336e3aa, with an explicit rationale for why a
halt matters to that decision). `run()` is a long-running loop (up to ~200 hosts) that writes
`HOST_QUARANTINE.json` via `quarantine()`/`release()` and `BINDING_HEALTH.json` via `_land`/
`_land_cas`, all without checking whether a library-wide halt is standing. I am not filing this
as a defect because the module's own doctrine (lines 30-33) frames quarantine as inherently
temporary and self-healing (`RETRY_AFTER_S`-bounded, explicitly reversible via `release()`),
unlike the non-reconstructible `WIKI_HOSTS.json` hostcheck.py gates on — so the two may simply
be held to different standards on purpose. Flagging so an owner can rule on whether
`binding_health.run()`'s writes should also be halt-gated.

Everything else read clean: `_land`/`_land_cas` digest-before-read ordering is correct throughout;
`quarantine()`/`release()` are genuine compare-and-swap with re-apply-on-refusal; `_spread`'s
even-sampling and `_candidate_titles`'s single source of truth are sound; `_fetch_chars`/
`_probe_present`/`_probe_absent` all correctly distinguish "errored", "clean negative", and
"resolved" rather than collapsing them; `run()`'s whole-estate-vs-partial-merge guards
(empty-hosts refusal, 0-host refusal, filtered-but-empty refusal, CAS on the partial merge) are
each independently sound and match their documented failure histories.

### roll.py (307 lines)

**Nothing further found beyond the KNOWN item above.** Audited `mutate()`'s CAS loop hard per
the brief's instruction (digest taken before read — correct; fails closed on unreadable/non-list
— correct, no `[]` substitution; `apply(rows)` is called fresh each attempt and is NOT wrapped
in a swallowing try/except, so `exclude()`'s `_apply` can raise `ValueError`/`_NoChange` straight
out of `mutate()` on the very first attempt, which is the documented contract, not a leak); temp
file names carry pid+thread+attempt so concurrent writers cannot collide on the scratch file;
`update_rows`'s `_apply` correctly treats "row found, nothing to change" apart from "row not
found" (order 60cb4e0e3595, already fixed). `exclude()`'s two code paths (`rows=` supplied vs.
not) return semantically different things under one boolean contract — "your in-memory copy
changed" vs. "it landed on disk" — but this is explicitly documented in the function's own
docstring and `exclude()` has zero callers in `src/` today, so I am not filing it; noting it only
because a future caller reading just the one-line "-> True if the roll was written" summary
could be misled by the `rows=`-supplied branch.

Separately (outside this batch, reported for awareness only, not filed): `handoff/run35/
checks_L4.py`'s own comment above the b3da16ddfe64 check (lines 80-85) still describes the
*old*, pre-fix `exclude()` behaviour ("it still calls `silence.write_json(ROLL, rows, ...)`
against the real, hardcoded ROLL path whenever `changed` is True") — current `exclude()` with
`rows=` supplied never writes to disk at all any more (roll.py:240-251). The comment is stale
relative to the code it sits beside, though the check itself still passes. Not fixed here since
`checks_L4.py` is not in this batch.

### scout.py (833 lines)

**Nothing found.** The shift's noted change — `_mutate`'s previously-silent
`except OSError: pass` on a stuck temp file now carries `silence.note("scout.py:mutate-tmp-
not-removed")` (line 179-185) — is in place and matches the documented pattern used by every
other exception arm in the same loop. Read `_mutate`'s CAS discipline, `verify()`'s three-way
failure classification (404/403/200-no-names), `scout()`'s sample-for-prompt-but-verify-against-
everything split, and `sweep()`'s stamp-before-work / restore-on-never-asked bookkeeping in
full; all internally consistent with their own documented histories and I could not construct a
scenario that defeats them.

### hostcheck.py (1636 lines)

Not in this shift's rewrite list; no fresh changes to audit here. Full read confirms the two
KNOWN items above are both still accurate and unchanged. No new defects found. `_land_hosts`'s
compare-and-swap, `_assert_not_halted` gating on every writing path (`--repair`, `--purge --go`,
`--adopt --go`, and re-asked immediately before `_land_hosts`'s own CAS per the 2026-09-08
ruling), and the write-verdict-capture chain through `sweep`/`purge`/`roster_audit`/`adopt` are
all sound on this read.

### gpu_lane.py (684 lines), anchors.py (576 lines), pantheon.py (432 lines)

**Nothing found.** Not in this shift's rewrite list and no open-queue hits. Read in full;
`gpu_lane.py`'s fail-open/staleness discipline (Windows-correct `_alive`, lease reclamation that
distinguishes "no file" from "corrupt file" from "live holder," `_take_slot`'s three-way
False/None/path return, heartbeat-covers-both-leases fix) held up under inspection. `anchors.py`
is a validation harness with no writes beyond `PANTHEON.json`-style artifacts it doesn't itself
own; its own invariant-grading logic (membership check, decimal-produced check, monotonicity,
per-anchor claims, college/bit-value grading) is internally consistent and I could not find an
unguarded lookup or a check that cannot fail. `pantheon.py`'s write-verdict and merge-failure
propagation to both stdout and the exit code are complete (no discarded verdict found).

### events.py (339 lines)

Beyond the KNOWN item above: **QUESTION (INFO-level)** — the module-level comment "A regex
escape eaten in transit is this project's oldest bug; every module carries the guard" (line 50)
overstates the current state of the tree. Measured: 50 of 118 `.py` files under `src/` carry the
`_BAD_CHARS` guard; several modules that actively use `re` do not (`feats.py`, `workorders.py`,
`drill.py`, `entity_match.py`, `weave_index.py`, among others). This is a claim about the
project as a whole, not about `events.py`'s own code, and I am not filing it as a defect against
this module — it does carry the guard itself — but the sentence reads as a stronger guarantee
than exists and could mislead a reader into skipping the check on a module that lacks it.

## Coverage stamp

Recorded via `sweep_plan.record("run58", [...], batch=16)` for exactly the eight modules listed
in the header table above — see the tool call in this session's trace. Call succeeded.
