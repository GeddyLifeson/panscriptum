# Sweep 48 — batch 05 audit

**Modules and lines read** (full read, top to bottom, no sampling):
- `src/feats.py` — 2732/2732 lines
- `src/allsweep.py` — 985/985 lines
- `src/custodes.py` — 698/698 lines
- `src/autostart.py` — 564/564 lines
- `src/pick_model.py` — 443/443 lines
- `src/grounding.py` — 361/361 lines
- `src/entity_match.py` — 310/310 lines
- `src/compress_store.py` — 149/149 lines

Total 6242 lines, matching `wc -l` for the eight files. Read-only against `src/`; no edits made,
`allsweep.py` and the mutation/verify scripts were not run.

---

## Finding 1 — MAJOR — `src/feats.py:698` — the documented http-404 exemption in `mined_under_failed_transport` is dead code

**What is wrong.** `mined_under_failed_transport()`'s own docstring (lines 677-685) states in so
many words: `"http-404" is NOT a failure here -- it is this file's one clean negative, the host
answering that there is nothing there.` The implementation is:

```python
tr = ((d.get("mined_under") or {}).get("transport")) or None
if tr:
    why = str(tr.get("why") or "unknown")
    return bool(tr.get("failed")) or why not in ("ok", "http-404", "raw-transport")
```

`why not in (...)` is the allowlist that is supposed to grant the http-404 exemption. But
`fetch()` (the function that produces `transport`, lines ~1479-1526) increments its `failed`
counter on *any* batch where `api()`'s own `outcome["ok"]` is False:

```python
if not _oc.get("ok"):
    outcome["failed"] += 1
    if outcome["why"] in ("unknown", "ok"):
        outcome["why"] = _oc.get("why") or "unknown"
```

and `api()` stamps `ok=False` for an http-404 exactly the same as for a genuine throttle/network
failure (`_stamp(False, "http-404")`, line ~1071). So whenever a batch's `why` ends up
`"http-404"`, `failed` is necessarily >= 1, and `bool(tr.get("failed"))` is already `True` before
the `or why not in (...)` clause is ever consulted — the allowlist can never override it because
it sits on the right side of an `or`. The only shape that is exempt in practice is
`"raw-transport"`, which `fetch()` special-cases to `failed: 0` explicitly (line 1500); http-404
gets no such carve-out and is therefore always treated as a failed transport, contradicting the
docstring's explicit claim.

**Effect.** A record whose fetch cleanly received "no such page" (http-404, nothing arrived) is
permanently re-mined on every load instead of being accepted as a clean negative — the opposite
of what `evidence_for`'s caching logic and this function's docstring both promise. This is a
"check that cannot fire as documented" (Hard Rule 0/priority-1 shape): the exemption clause is
structurally unreachable given how its only producer (`fetch()`) computes `failed`.

**How verified.** Traced the full data flow: `api()`'s `_stamp(False, "http-404")` (feats.py
~1071) -> `fetch()`'s per-batch accounting (`outcome["failed"] += 1` whenever `not _oc.get("ok")`,
feats.py ~1512-1516) -> `evidence_for()` storing `transport` verbatim into
`mined_under.transport` (feats.py ~2183) -> `mined_under_failed_transport()`'s read of that same
dict (feats.py 691-700). Confirmed by grep that `"failed"` is set in exactly one place
(`fetch()`, line 1514) and that no other code path produces `failed: 0` alongside `why:
"http-404"`.

**Proposed remedy.** Either (a) have `fetch()` not count an http-404 batch as `failed` (mirroring
the `raw-transport` special-case), or (b) change the check in `mined_under_failed_transport` to
key off `why` alone (`why not in ("ok", "http-404", "raw-transport")`) without the `bool(failed)`
disjunct, since `why` already carries the same information the docstring is reasoning about.

---

## Finding 2 — MAJOR — `src/allsweep.py:610-648` — the RECONCILE process check has no way to say "could not tell", so a blind WMI probe reports the whole job roster as down

**What is wrong.** In `reconcile()`'s "what is actually running right now" block:

```python
r = subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" | "
                    "ForEach-Object { $_.CommandLine }"],
                   capture_output=True, text=True, timeout=120,
                   encoding="utf-8", errors="replace", creationflags=_NO_WIN)
live = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]
...
for job in _ON.ALL_JOBS:
    n = sum(1 for ln in live if _ON._cmd_is_running(job, ln))
    ...
    else:
        note("NOT RUNNING", job, 0)
```

`r.returncode` is never inspected, and an empty/garbage `r.stdout` is treated identically to a
process table that was genuinely walked and found no matches — every job in `_ON.ALL_JOBS`
reports `NOT RUNNING` if the PowerShell/WMI call comes back empty for any reason (WMI service
down, a permissions issue, a non-terminating PowerShell error that leaves stdout empty without a
nonzero exit code, etc.). `subprocess.run` does not raise on a nonzero return code by default, so
this failure mode is not caught by the surrounding `except Exception as e:` at all — it silently
produces a "roster" of exclusively-down jobs.

This is exactly the fault class this same codebase already diagnosed and fixed for the identical
WMI call in `src/overnight.py`'s `_proc_lines()` (order 1d556b6ef535), whose own docstring states
the house rule directly: *"THREE ANSWERS, NOT TWO... An unknown is NOT cached"* and whose code
explicitly checks `if r.returncode != 0 or not (r.stdout or "").strip(): return None`, propagating
a real tri-state (`True`/`False`/`None`) up to `autostart.supervisor_alive()` and every other
caller. `allsweep.py`'s own process-check block (same `Get-CimInstance Win32_Process` /
`ForEach-Object { $_.CommandLine }` shape, same failure surface) has none of that guard — it is
the twin of the exact sensor this project has already had to fix once, left unfixed on the other
side of the tree.

**Effect.** A single flaky or denied WMI call turns into a RECONCILE report claiming every
managed job — dashboard, publish, foreman, overwatch, pipeline, overnight, autostart, everything
in `_ON.ALL_JOBS` — is `NOT RUNNING` simultaneously, which is indistinguishable on the page from a
genuine total outage. (`main()` does not fold these `NOT RUNNING` rows into the sweep's exit
code — the comment at line ~646 notes "Reported, not counted as a bad subsystem" — so this does
not flip the sweep red, but it does hand an operator a false "everything is down" reading in the
console/`ALLSWEEP.json` reconcile table, which is the "instrument that cannot see the work"
failure this run's brief calls out by name.)

**How verified.** Read `reconcile()`'s block end to end (allsweep.py 608-649) and confirmed no
`r.returncode` reference and no early return/None-propagation anywhere in the block or its
`except`. Cross-checked against `overnight.py`'s `_proc_lines()` (overnight.py ~108-155), which
performs the same `Get-CimInstance Win32_Process` enumeration and explicitly guards both
`returncode != 0` and empty stdout, returning `None` (not `False`) on either — the pattern this
block lacks.

**Proposed remedy.** Mirror `overnight._proc_lines()`'s guard: check `r.returncode` and treat an
empty/failed read as "could not determine" (e.g. `note("process check UNAVAILABLE", ...)`) rather
than iterating `_ON.ALL_JOBS` and reporting `NOT RUNNING` for each. Simplest fix: reuse
`overnight._proc_lines()`/`overnight.running()` directly instead of re-spelling the WMI call here,
which would also collapse two independent copies of the same sensor into one (this file's own
`_marked()` docstring already argues for exactly that kind of hoist elsewhere).

---

## Finding 3 — MINOR — `src/allsweep.py:326,346` — unmarked 150-character truncation of the IMPORT tier's failure diagnostic

**What is wrong.** In `check_import()`:

```python
tail = (r.stderr or "").strip().splitlines()
err = tail[-1][:150] if tail else f"rc={r.returncode}"
...
ok, err = False, "exited without a traceback, saying: " + said.splitlines()[-1][:150]
```

Both cuts are silent — no "…", no length disclosure, no full copy stored anywhere else. This
`err` string is the *only* representation of the failure that reaches the console and
`ALLSWEEP.json`'s `imports` list (there is no `tail`/`lines_total` field for the IMPORT tier the
way `run_verifier()` provides for VERIFY-tier rows). This is the same shape of cut this exact file
spent several orders correcting elsewhere in itself — `_marked()`, `verifier_console_lines()`,
`art["bad"][:25]`'s disclosed cut, the ESTATE-row `_marked()` calls — all of which this file's own
comments insist must either keep the whole value or mark the cut. This one spot was not brought
in line with that discipline.

**How verified.** Read `check_import()` (allsweep.py 306-345) in full; confirmed `err` is the sole
field returned for a broken module (`{"module": name, "ok": ok, "detail": err, ...}`) and that no
other field on that dict carries the untruncated line.

**Severity note.** In practice the last line of a Python traceback is usually short
(`NameError: name 'x' is not defined`), so this is a low-probability trigger — hence MINOR rather
than MAJOR — but a `SyntaxError` (which echoes the offending source line plus a caret) or an
`AssertionError`/`KeyError` carrying a long value can exceed 150 characters, and on this exact
project's stated policy an unmarked cut on the one diagnostic field a person reads to find a
broken module is worth naming.

**Proposed remedy.** Either raise the cut to something generous and mark it (`… (N more chars)`),
or — cheaper — store the untruncated line as a second field (e.g. `"detail_full"`) in the returned
dict the way VERIFY-tier rows keep `tail`/`lines_total` alongside the console-bounded view.

---

## What I read and found nothing wrong in

- `src/custodes.py` (full 698 lines) — extremely well self-audited; every place I traced a
  suspicious pattern (the `tilt=0.0`/`evidence_sensitivity` coupling, the `staleness_widening`
  None-vs-zero distinction, the Threnody veto's `eta is None` handling, `table_faults()`'s own
  battery-hook gap) turned out to already be the subject of a resolved order and correctly
  implemented as described. No new defect found.
- `src/autostart.py` (full 564 lines) — `supervisor_alive()`'s tri-state handling, the
  `_twin_watchdog()` retry/fail-open logic, `install()`/`uninstall()`'s atomic-write and
  denied-replace handling, and the `--status` tri-state printing (`"running" if _up else ... if
  _up is None else "not running"`) were all traced and are correct — the truthiness-looking
  chained conditional is safe because only literal `True` triggers the first branch. No new
  defect found; this module's own known-fixed history (the quoted-path `overnight.running()` bug)
  is not reproduced elsewhere in the file.
- `src/pick_model.py` (full 443 lines) — the `resident()`/`fit_note()` split between "total VRAM
  budget" and "free VRAM right now", the `vram_measured` provenance flag, and
  `save_config()`'s gated atomic write were all traced and are consistent and correctly gated.
- `src/grounding.py` (full 361 lines) — `classify_text`/`classify_source`'s Hard-Rule-0 fixes
  (uncapped ranking, full-field confidence denominator, the synthesis-blob exemption) are
  correctly implemented as documented; the uncapped `low`/`runners_up` printing in `main()` is
  genuinely uncapped.
- `src/entity_match.py` (full 310 lines) — the qualifier-compatibility gate, the
  `STRONG`/`WEAK` threshold assertion, and the `candidates()` return-shape consistency
  (`blocked_by_qualifier` always a dict) all check out.
- `src/compress_store.py` (full 149 lines) — the atomic write, PID+thread-qualified temp name,
  temp cleanup on both failure paths, and `load()`'s content-hash verification against the
  filename are all correctly implemented.
- `src/allsweep.py` — the VERIFIER `rc_means` grading (`RC_BROKEN`/`RC_FINDINGS`), the ESTATE-tier
  fault grading (`_row_is_fault`, fail-closed default), the LINT tier's did-not-complete detection
  (`lr.returncode not in (0, 1)`), and the RECONCILE tier's other five checks (source/host
  reconciliation, coverage staleness, cache-directory orphans, roster purges, phase
  implementation, band-ceiling violations) were all read in full and are internally consistent
  with their extensive inline documentation. The two issues above (findings 2 and 3) are the only
  defects found in this file.
- `src/feats.py` — beyond finding 1, the rest of the module (host resolution/override ordering,
  `_api_list_all`'s continuation-following and `_CAP_BOUND` accounting, `discover()`/
  `resolve_title`'s ranking-not-truncating behaviour, `_QUANTITY`'s exponent group numbering,
  `_unwrap_templates`'s brace/param-brace handling, `strip_wikitext`'s table-cell preservation,
  the four `mined_under_*` staleness predicates other than finding 1, `roll()`'s counter
  bookkeeping and deferred-tail handling, and `main()`'s exit-code wiring) were all traced and
  are consistent with their documentation. No stale `file.py:NNN` citations were found pointing
  at drifted line numbers in any of the eight files — the citations checked (e.g. the
  `verify_math.py:6824-6825` reference in `allsweep.py`, the `magnitude.py:417/45/640` and
  `zfighters.py:302,328,365` references in `feats.py`) were not independently re-verified against
  those other files' current line numbers, since those files are outside this batch's assignment.
