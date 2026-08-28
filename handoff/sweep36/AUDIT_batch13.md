# Batch 13 audit — run #36

Modules: dashboard.py, binding_health.py, escalation.py, onomast.py, backfill.py, navtree.py,
profile.py, audit.py

Read-only. No source files edited. The standing halt (`DRILL_BREACH`, raised by `drill.py`,
`raised_at` 1787889054) was observed via `escalation.status()` for context only — not touched,
not cleared.

---

## escalation.py — total care, per the brief

Read the whole file (515 lines) end to end, including every branch of `escalate()`, `clear()`,
`_by_a_person_at_the_cli()`, `_raise_halt()`, `_read_halt_raw()`, `stop_subsystem()`,
`_read_stopped()`, `subsystem_stopped()`, `resume_subsystem()`, and `main()`.

### Property (a) — clear() validates the ruling before the caller: CONFIRMED, no defect

Lines 443-446:
```
if not ruling or not str(ruling).strip() or len(str(ruling).strip()) < 12:
    raise ValueError(...)
if not _by_a_person_at_the_cli():
    raise PermissionError(...)
```
The ruling check runs first, exactly as the docstring (lines 438-441) says it must, so `clear("")`
and `clear("ok")` both raise `ValueError` regardless of caller — which is what `drill.py`'s probe
of this rule actually needs to observe.

`_by_a_person_at_the_cli()` itself (lines 401-429) requires BOTH `sys.modules["__main__"].__file__`
to resolve to `escalation.py`'s own absolute path AND the grandparent stack frame to be named
`main` in that same file. I tried to find a bypass reachable through ordinary misuse (an import
alias, `from escalation import clear`, `getattr(escalation, "clear")()`, a wrapper script that
imports and calls `escalation.main()` under a borrowed argv) and every one of them is blocked by
condition 1 alone, because the importing script's own `__main__.__file__` is never
`escalation.py`. The only bypass I could construct requires the caller to already have arbitrary
code execution in-process (manufacturing a fake `__main__` module and a code object with a forged
`co_filename`/`co_name` via `types.CodeType`/`code.replace`) — at which point the attacker could
equally monkeypatch `_by_a_person_at_the_cli` itself or write `state/HALT.json` directly, so this
isn't a meaningful additional hole. Noting as a QUESTION, not a defect: the guarantee is sound
against the actual threat model in the docstring (an autonomous run reasoning its way to an
import-based bypass), not against deliberate low-level frame forgery.

### Property (b) — fail closed on an unreadable/corrupt halt file: ONE FINDING (MAJOR), ONE FINDING (MINOR)

**MAJOR — `_read_stopped()` (rung-4 "STOPPED" ledger) fails OPEN, not closed, on a
valid-but-non-dict `STOPPED.json`.**

Anchor text, `escalation.py` (`_read_stopped`, ~line 332-342):
```python
def _read_stopped():
    try:
        with open(STOPPED, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        # UNREADABLE MEANS STOPPED, for everything. The file only exists to say what must not
        # run, so failing to read it cannot be permission to run things.
        return {"__unreadable__": {"reason": "STOPPED.json could not be read", "at": time.time()}}
```
The docstring's own guarantee is "UNREADABLE MEANS STOPPED, for everything" — but that guarantee
is wired to the `except Exception` branch only. If `state/STOPPED.json` parses as valid JSON that
is not a dict (a list, a string, a bare number — no exception is raised by `json.load`), the
function silently downgrades it to `{}` via the `isinstance` check, which is NOT the
`__unreadable__` sentinel. `subsystem_stopped(name)` then reports every subsystem as **not**
stopped.

Reproduced directly:
```
STOPPED.json content: ["not","a","dict"]
_read_stopped()        -> {}
subsystem_stopped("x") -> (False, '')
```
This is the opposite of "unreadable means stopped" — a malformed-but-parseable ledger is read as
"nothing is stopped," i.e. fail OPEN. In production this file is only ever written by
`_write_stopped()` (always a dict), so the practical trigger is hand-editing or a bug elsewhere
that writes garbage — but the whole point of a fail-closed contract is to cover exactly that case,
and this is the one path in the module where the code does the opposite of what its comment,
three lines above it, promises.

**MINOR — `_read_halt_raw()`/`status()`/`assert_clear()` crash with `AttributeError` rather than
returning the documented halted-state, on the same class of input (valid JSON, wrong type).**

Anchor, `_read_halt_raw()` (~line 267-279): the `except Exception` only wraps `json.load`, so a
`state/HALT.json` that parses to e.g. a JSON list is returned as-is (no exception). `status()`
(~line 282-287) then does `rec.get("cleared", False)` unconditionally, which raises
`AttributeError: 'list' object has no attribute 'get'` instead of returning `(True, rec)`.

Reproduced:
```
HALT_FILE content: [1, 2, 3]
_read_halt_raw() -> [1, 2, 3]          (no exception)
status()         -> AttributeError: 'list' object has no attribute 'get'
```
I checked every current caller of `assert_clear()`/`status()` in `src/` (dashboard.py,
binding_health.py is not a caller, feats.py, foreman.py, overnight.py x2, overwatch.py,
pipeline.py, publish.py, read.py, local_agent.py) to see whether this crash is actually swallowed
anywhere and lets execution continue while "halted" reads as false — it is not: every bare call
site has no surrounding try/except so the `AttributeError` propagates and kills the process
(functionally equivalent to halting, just with an unhelpful traceback instead of the intended
`SystemHalted` message), and `overnight.py`'s one guarded call site (line 966,
`except Exception as e: log(...); break`) catches `AttributeError` too and correctly breaks the
cycle loop. So I did **not** find a path where this silently continues running. But it does
contradict the docstring's explicit claim (lines 31-32: "an unreadable or malformed HALT file is
treated as halted") for this specific malformed shape, and it would defeat
`verify_math.py`'s own self-test at line 4928 (`except _esc20p.SystemHalted as _e20p:`), which
catches only the intended exception type and would itself crash uncaught if the live halt file
were ever this shape. Classed MINOR rather than MAJOR because no fail-open behavior was found in
current callers, unlike the STOPPED.json case above.

### Everything else in escalation.py

- `escalate()`'s name/number coercion for `level` (lines 165-182) and its "unrecognised level
  lands at MANAGER, not OWNER" behavior: read carefully, matches the extensive comment exactly —
  traced both the string and non-string bad-value paths by hand.
- `_raise_halt()`'s discarded-verdict fix (checking `silence.write_json`'s return and printing to
  stderr on denial) and the "second fault while halted is appended as `also`, never replaces the
  first" behavior: correct as written.
- `stop_subsystem()`/`resume_subsystem()`: `resume_subsystem` requires a >=20-char ruling before
  touching disk, matching `clear()`'s discipline; `stop_subsystem`'s own failure-to-record path
  correctly escalates to OWNER rather than leaving a silent gap.
- `brief()`'s per-rung field whitelist: consistent with the "only OWNER gets `evidence`" design
  and I didn't find a field leaking to a rung not listed for it.

No edits made. The standing halt was not touched.

---

## binding_health.py (edited today — compare-and-swap merge)

Read in full (719 lines). Focus on `_land_cas()`, `run()`'s partial-pass merge, and the two
newest doc-comments (the discarded-verdict fix in `_land`, the shared-tmp-name fix, the
compare-and-swap merge itself).

- `_land_cas()`: reads `prior_digest = silence.digest_of(OUT)` **before** reading the file's
  content for `prior` (line 636), matching its own docstring's requirement ("READ THE DIGEST
  BEFORE THE CONTENT, so a file that moves between the two cannot be merged into silently"). The
  temp file name includes both pid and thread id. On a CAS refusal the temp file is unlinked
  (`_unlink(tmp)`), not left as litter. `run()` checks the `(landed, why)` return and reports the
  refusal to the caller rather than claiming success — verified, not a discarded verdict.
- `verdict()` (the pure three-probe decision function): traced every branch by hand against the
  worked examples in its own comments (the `ok_absent is None` short-circuit, the
  "answers yes to everything" case, the "up but binding suspect" case). All consistent, no logic
  error found.
- `_probe_present`'s `PRESENT_CANDIDATES` bound: this is a `[:PRESENT_CANDIDATES]` slice (line
  265) and a `len(out) >= want` early return in `known_present_titles`. Both are read as
  deliberate, documented bounded-probe design (an existence check — "does ANY known title
  resolve" — not a roster being displayed or decided on), not a Hard Rule 0 violation. Flagging
  as a QUESTION rather than a defect given how explicitly the docstring reasons about exactly
  this tradeoff.
- QUESTION, not a defect: a failed `_land`/`_land_cas` write to `BINDING_HEALTH.json` is reported
  to stderr but not escalated through `escalation.py`, unlike a failed `quarantine()` write to
  `HOST_QUARANTINE.json`, which does raise `ESC.escalate(ESC.SUPERVISOR, "HOST_QUARANTINE_NOT_RECORDED", ...)`.
  `BINDING_HEALTH.json` is a report file rather than a behavior-controlling ledger, so the
  asymmetry may well be intentional (the module's own extensive commentary about "a lie in the
  escalation ledger" suggests the omission was considered) — worth a person confirming rather
  than assuming either way.

No other defects found.

---

## dashboard.py (panelSafety — two caps removed today; checked none remain)

Read `panelSafety()` end-to-end (lines 801-902) plus its server-side data source, `_safety()`
(lines ~486-575) and `_watch()` (lines 310-329, the sibling panel the "cap ruled a truncation"
comment references).

Confirmed both previously-capped lists in `panelSafety` are now uncapped, with the comments
documenting the fix left in place:
- `br.forEach(x=>s.appendChild(...))` (line 869) — every breached net, comment: "EVERY breached
  net, not the first six... a cap here made the page contradict itself."
- `Object.keys(qn).forEach(h=>...)` (line 892) — every quarantined host, comment: "the label
  counts them all, and a host whose name never appears cannot be un-quarantined by anyone reading
  this page."

Whole-file grep for `[:N]`-shaped slices in `dashboard.py` turns up exactly three, and all three
are text-length truncations of a description/error field for one already-fully-listed row, not
roster caps:
- `(f.get("actual") or "")[:160]` (line 324, in `_watch()`) — the finding is still one row of
  `out["findings"]`, which is `[... for f in openf]` with the comment "ALL open findings -- a
  monitoring cap ruled a truncation, 2026-08-24" (line 326).
- `r.get("reason", "")[:120]` (line 545, in `_safety()`) — every quarantined host's dict key is
  still present; only its reason string is shortened for display.
- `str(e)[:120]` (line 962) — an error message in the HTTP handler, unrelated to any roster.

No remaining caps, server- or client-side, in `panelSafety` or its data path. `--audit`'s
`--sample`-shaped table isn't in this file, so not applicable here.

---

## backfill.py (sort key inversion — verified against the comment's own worked example)

Read in full (328 lines).

The current key, line 213:
```python
missing = sorted(missing, key=lambda t: (t in sizes, -sizes.get(t, 0)))
```
Traced by hand against the comment's own worked example (sizes={A:100, C:5}, B unmeasured):
`key(A)=(True,-100)`, `key(C)=(True,-5)`, `key(B)=(False,0)`. Ascending sort puts `False` before
`True`, so B (unmeasured) sorts first; within the `True` group, `-100 < -5` puts A before C.
Result: `[B, A, C]` — **exactly** what the comment (lines 204-212) claims the fixed key produces,
and re-deriving the old buggy key (`t not in sizes`) by hand gives `[A, C, B]`, also exactly
matching what the comment says the old key produced. The fix is correct and does what its comment
says.

Also checked:
- `--cap` defaults to `None` (line 277: `default=None`), and `roster(host)` is called with no
  `limit` (line 177), so the category-walk itself stays uncapped by default, matching Hard Rule 0.
- `roster()`'s own docstring and code (lines 68-123) walk `Category:Characters` and one level of
  subcategory with `cmlimit=500` pagination and no truncation of the final list — verified no
  `[:N]` slice survives except the final `return out[:limit] if limit else out`, which only fires
  when a caller explicitly passes a `limit` (never done from `backfill_source`).
- `RosterIncomplete` is raised, not silently returned, when the category walk stops on a network
  failure rather than the end of the listing — correct, and its caller (`main()`'s `--all` loop)
  does catch and report it per-source rather than losing the whole run.

QUESTION, not a defect: `main()`'s `--audit` printer (line 291) does `for x in rows[:26]:` with an
explicit "... and N more" line (line 293-294) for a ranked-by-share list of sources. The
underlying `audit()` return value is the full, uncapped list — only the console table is
shortened, with the omission disclosed. Given Hard Rule 0's blanket wording this is worth a
person's eyes, though it matches the same disclosed-remainder convention used in `onomast.py`'s
and `audit.py`'s own console output (see below), which reads as this project's established
practice for terminal display rather than a new violation.

---

## onomast.py (edited today) — one finding (MAJOR)

Read in full (438 lines).

**MAJOR — the `taken`-seeding protection against reused catalogue names only survives ONE
generation cycle, not indefinitely as its own comment claims, because `main()`'s write overwrites
`ONOMASTICON.json` with only the current run's `named` dict.**

`name_worlds()` (lines 337-399) contains an extensive comment (lines 350-365) explaining exactly
why `taken` must be seeded from designations already on disk for cids that have since dropped out
of `resolved` — otherwise "two runs... can independently hand the same catalogue_name to two
different worlds," and "a world dropped from `resolved` this run keeps its old designation alive
in already-published prose while its name silently becomes free for a new, unrelated world to be
coined into." The seeding code (lines 366-378) does correctly protect the CURRENT run from
reusing a name still standing in `ONOMASTICON.json`.

But `main()` (lines 402-434) writes only `named` — the dict `name_worlds()` returns, which
contains entries **only** for cids currently in `resolved` (line 388: `out[cid] = {...}` inside
`for cid, v in sorted(items, ...)`, itself inside `for key, items in sorted(by_key.items())`
gated on `if len(items) < 2: continue`) — as the entire new content of `ONOMASTICON.json` via a
blind `silence.write_json(OUT, named, ...)` (line 428). A cid that drops out of `resolved` between
two runs is *never* written back, even though the very seeding logic just used it to block a
collision this run.

Reproduced end to end (temp `ONOMASTICON.json`, using the module's real `name_worlds`/`write_json`):
```
run 1: resolved = {cid_X: Earth(group gX), cid_Y: Earth(group gY)}
       named -> {cid_X: 'Cauria', cid_Y: 'Brostadock'}; file written with both keys.

run 2: resolved = {cid_Y: Earth(group gY), cid_Z: Earth(group gZ)}   # cid_X dropped
       named -> {cid_Y: 'Brostadock', cid_Z: 'Venuallora'}
       file written for run 2 contains ONLY ['cid_Y', 'cid_Z'] — cid_X/'Cauria' is gone.
```
So the protection described in the comment holds for exactly the one run immediately after a cid
drops out (because that run's seeding still reads the old file, which still has it) — but the
write on that very same run erases the record that made the protection possible, so on run 3 the
name "Cauria" is free again and nothing stops a new, unrelated world from being coined into it,
silently orphaning any already-published prose that cites `cid_X`'s old shelfmark by that name.
This is precisely the failure the comment says the seeding exists to prevent, reintroduced by the
write immediately after the seeding runs. The comment's claim of protection across "two runs...
after `resolved` has grown or shrunk between pipeline passes" (implying an arbitrary number of
passes) is not what the code delivers — it delivers protection for exactly one pass past the drop.

A fix would need `main()` to merge `named` over the previously-standing entries for cids not in
`resolved` (mirroring exactly the seeding it already does for `taken`), rather than replacing the
file wholesale — but per the sweep's read-only rule this was not attempted here.

Everything else in `onomast.py` (the syllable generator `coin_name`/`well_formed`,
`coin_well_formed`'s already-fixed fallback-invariant bug, `register_for`'s genre/feature voting
and its documented tie-break-toward-source rule) was read and traced against its own worked
examples; no further defects found. The console `[:4]`/`[:9]` truncations in `main()`'s printed
report (lines 418, 421) are display-only with disclosed remainders (line 425), not roster caps —
the written `ONOMASTICON.json` itself carries every named world.

---

## navtree.py — read, nothing found

Read in full (284 lines), including the three historical-bug callouts in the module docstring
and the two "m41"/"m11" determinism fixes in `sources_under()` and `register_for()`.

- Traced `sources_under()`'s `path == key or path.startswith(key + ".") or key.startswith(path + ".")`
  against the m11 bug it describes (a source at "0.1.2" wrongly counted as an ancestor of
  "0.1.20"): with the `+ "."` on both arms, "0.1.2".startswith("0.1.20.") is False and
  "0.1.20".startswith("0.1.2.") is also False, so they correctly do not match as ancestor/
  descendant of each other. Correct.
- Traced the `register_for`/hyperverse-naming tie-breaks (`max(set(regs), key=lambda r:
  (regs.count(r), r))`): using the register/grounding-type string itself as the secondary sort
  key makes the result deterministic across runs (no hash-order dependency), matching the "m41,
  75 of 734 nodes renamed" bug it replaced.
- Checked whether `empty = [k for k, v in nodes.items() if v["n"] == 0]` (line 253, labeled
  "branches holding sources but no catalogued worlds yet") could ever include a node with no
  sources either (which would mislabel it): traced `touch()`'s call sites in both the sources loop
  (lines 89-97) and worlds loop (lines 100-109) and confirmed every node that ever enters `nodes`
  is touched at the same path-length where its counter (`src` or `n`) is incremented in the same
  loop iteration — a node can never exist with both `src==0` and `n==0`, so `n==0` does imply
  `src>=1` by construction. Label is accurate.
- `audit()`'s child-sum invariant (`s = sum(nodes[c]["n"] for c in v["k"] if c in nodes)`)
  correctly skips a missing child rather than raising `KeyError` on it (its own comment explains
  why), and still separately reports that child as `"{k}: child {c} has no node"` — not silently
  dropped.
- No `[:N]` truncation of `worlds`/`sources`/`nodes` anywhere; the two console `[:N]`s in `main()`
  don't exist in this file (checked — none found; the module writes a state audit file listing
  every problem, no cap).

No defects found.

---

## profile.py — read, nothing found

Read in full (222 lines).

- The round-trip check in `main()` (lines 196-208) was already fixed from a genuine tautology to
  a real check — its own comment explains the old bug (`d["profile"] != r["profile"]` compared
  decode's own echoed argument to itself and could never fail) and the new code re-encodes what
  `decode()` extracted and compares that to the original string. Verified this is a real
  round-trip now, not a tautology.
- `B32`'s 32-symbol Crockford alphabet and the `_b32`/`_unb32` mask history (comment at lines
  52-65) checked against current code: `_b32` masks with `n & 31` so it can only ever emit valid
  indices; `_unb32` uses `B32.index(ch)`, which raises `ValueError` (loudly) rather than silently
  miscoding for a character outside the alphabet.
- MINOR/cosmetic, not filed as a defect: `decode()`'s regex (line 109) uses the loose character
  classes `[0-9a-z]+` and `[0-9a-z]{4}` for the address and feature groups, which admit `i`, `l`,
  `o`, `u` — characters outside the real B32 alphabet. A corrupted profile containing one of those
  still passes the regex and only fails later inside `_unb32`/the feature-table lookup, with a
  generic `ValueError: substring not found` rather than the friendlier
  `"not a world profile: ..."` message the regex mismatch produces. Still fails loudly either way
  — this only affects the error message's specificity, not correctness.

No defects found.

---

## audit.py — read, nothing found

Read in full (188 lines).

- `_JUNK` regex (lines 41-43) checked against the specific bug its comment describes (a shared
  trailing `\b` making the whole group a prefix test, so "Timeline of the Fallen Empire" and
  "Gallery of Rogues" wrongly matched): confirmed the alternatives split correctly between
  whole-name-only (`gallery$`, `navigation$`, etc.) and legitimate-prefix (`category:`,
  `list of `, `characters?\b`) forms, and `"Gallery of Rogues"` does NOT match `gallery$` since
  the pattern requires end-of-string immediately after "gallery".
- The console-truncated violation examples (`for x in v[:4]:`, line 156, with "... and N more" at
  line 158-159) are display-only: `total_f` (line 160, the reported total) and the `fails` dict
  itself retain every occurrence, matching the same disclosed-remainder convention seen in
  `backfill.py` and `onomast.py`'s console output above.
- MINOR/cosmetic, not filed as a defect: `rate = len(v) / max(1, stats["entries_catalogued"])`
  (line 153) — in the edge case of a synthesis-level failure existing while zero entries are
  marked `catalogued` anywhere, the `max(1, ...)` guard against division-by-zero would produce a
  nonsensical inflated percentage (denominator forced to 1) rather than reflecting a genuine zero.
  This doesn't hide or miscount any violation — `len(v)` itself, the actual occurrence count, is
  unaffected — only the parenthetical rate display would misread in an unlikely combination that
  the current pipeline shape probably never produces (synthesis without any catalogued entries).

No defects found.
