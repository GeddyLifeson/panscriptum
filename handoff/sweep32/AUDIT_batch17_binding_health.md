# Audit — src/binding_health.py (256 lines, full read) — sweep run32, batch 17

## Wiring status: NOT WIRED IN (confirmed)

`grep -rln "binding_health" .` (repo-wide, excluding `.git/`) returns only:
- `src/binding_health.py` itself
- `HANDOFF.md` (prose noting the same fact)

No file under `src/` imports `binding_health`, calls `binding_health.run()`,
`binding_health.canary()`, `binding_health.quarantine()`, `binding_health.quarantined()`, or
`binding_health.is_quarantined()`. It is not referenced by `foreman.py`, `overwatch.py`,
`pipeline.py`, `sweep_plan.py`, `verify_math.py`, or `drill.py`. It is a standalone CLI
(`if __name__ == "__main__"`) that nothing in the pipeline currently invokes.
**Finding: dead code as shipped.** Its entire quarantine mechanism (`HOST_QUARANTINE.json`) is
inert — nothing consults it to decide whether to trust a host's silence, which is precisely the
failure mode the module's own docstring (lines 1–37) says it exists to close. Severity: MAJOR
(not BLOCKING only because it is inert rather than actively wrong — but it delivers zero of its
stated value until something calls it).

Also note: the module does **not** `import threading` anywhere (grep confirms zero hits). The
audit brief's expectation that this module "uses threading" does not hold for the code as
written — flagging this explicitly since the brief asked to check it.

---

## BLOCKING

**binding_health.py:146-151 — `_probe_absent` treats ANY exception as a PASS ("correctly absent"), defeating the one check whose entire job is to catch a rotted binding.**

```python
def _probe_absent(host, timeout=25):
    try:
        import feats as F
        got = F.fetch(host, [ABSENT_PROBE])
    except Exception:
        return True, "no answer, which is the correct answer"
    if got:
        return False, (...)
    return True, "correctly absent"
```

The module's own docstring (lines 26–28, 137–141) states the absent-probe exists to catch "the
host says yes to everything... a soft-404, a search page, a login wall dressed as an article."
But if `F.fetch` *raises* on the absent title — for any reason at all, including a parser bug
tripped by a malformed response, an unrelated `TypeError`/`KeyError` inside `feats.py`, or a
transient error that has nothing to do with absence — the code converts that raise into
`(True, "correctly absent")`, i.e. a pass. This is CLAUDE.md's own "check that cannot fail" and
"swallowed failure" categories at once: a genuinely rotted/soft-blocking host that happens to
throw instead of returning a truthy blob on the nonsense title silently clears the absent-probe.

Concretely: if `_probe_present` also succeeds (`ok_p=True`) on that same host — plausible, since
present-probe and absent-probe hit different URLs and a host can misbehave on one path and not
the other — then `healthy = ok_p and ok_a = True and True = True`. The host is certified healthy
by the exact mechanism designed to prevent that certification. Compare: `_probe_present`
(binding_health.py:117-133) converts the same kind of exception into `False` (correctly
unhealthy) — the two probes handle an identical failure mode in opposite, asymmetric ways, and
the asymmetry is on the side that can never fail. VERIFIED (read directly; logic traced against
docstring's own stated purpose).

**binding_health.py:73-76 — `_land` hand-rolls the tmp-file name (`path + ".tmp"`) instead of using `silence.write_json`, reproducing this project's own named "costliest recurring defect."**

```python
def _land(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=True, ensure_ascii=False)
    silence.replace_retry(tmp, path)
```

`silence.write_json` (src/silence.py:290+) exists specifically because this exact pattern —
`path + ".tmp"` with no PID/thread qualifier — was found at twelve call sites in the 2026-08-25
sweep and documented as the cause of one writer's temp file clobbering another's mid-write
(silence.py:302-306: "Two writers of the same path otherwise collide on the temp file itself,
and the loser can replace the winner's target with a partial file"). `_land` does call
`silence.replace_retry` for the final atomic rename (so it is not the *worse* bare-`os.replace`
variant), but the unqualified tmp name means two concurrent `binding_health` processes/threads
writing `QUARANTINE` or `OUT` at the same time can still collide on the shared `.tmp` path before
the rename ever happens. Given `quarantine()`, `release()`, and `run()` all route through
`_land`, and the module is explicitly meant to run as part of a sweep alongside up to sixteen
concurrent batches (per this project's own `sweep_plan.py` precedent), this is a live hazard, not
a hypothetical one. Fix is mechanical: call `silence.write_json(path, obj, sort_keys=True)`
instead of hand-writing `_land`. VERIFIED.

**binding_health.py:90-98, 109-114, 223 — unguarded read-modify-write on shared `HOST_QUARANTINE.json` (and `BINDING_HEALTH.json`) with no lock — the exact race this project already found and fixed in `sweep_plan.py`.**

`quarantine()` and `release()` both do `_load(QUARANTINE, {})` → mutate a dict in memory →
`_land(QUARANTINE, q)`, with no lock and no per-writer sharding. `sweep_plan.py`'s own docstring
(src/sweep_plan.py:126-141) describes this precise shape as a bug it already had and fixed:
"The first version did an unguarded read-modify-write and lost the loser's modules... Two of
them interleaving read-modify-write still drops one batch's modules." `binding_health.run()`
iterates every bound host in a single-threaded loop today, so nothing in the current code path
triggers this — but the module is designed to canary ~200 hosts before/alongside a sweep, and if
it is ever invoked more than once concurrently (e.g. two batches each canarying a subset of
hosts, or a scheduled canary racing an ad-hoc `--host` run), two processes can each read the same
`HOST_QUARANTINE.json`, each add a different host's quarantine entry, and each write back —
the second writer's `_land` overwrites the first writer's addition, silently losing a quarantine
record for a rotted host. Severity BLOCKING because it is the identical defect class the project
has already paid for once (sweep_plan.py) and documented explicitly as the fix pattern to use
(per-writer shard file + merge-at-read, not shared read-modify-write). VERIFIED (logic read
directly; pattern match against sweep_plan.py's own postmortem).

---

## MAJOR

**binding_health.py:117, 136 — `timeout=25` parameter on `_probe_present`/`_probe_absent` is dead: never passed to `feats.F.fetch`, and `feats.fetch(host, titles)` (src/feats.py:428) accepts no `timeout` kwarg at all.**

Both probe functions declare `timeout=25` and never reference the local variable again. The
actual network timeout is whatever `endpoint.py`'s `_get()` hardcodes per call site (25s/40s/45s
depending on internal path — src/endpoint.py:108,205,329), which `binding_health.py` has no way
to influence despite appearing to expose a `timeout=` knob. This is misleading rather than a hang
risk (a real timeout does exist, just not the one the caller thinks they're setting), but it is
exactly the "comment/code contradiction" class the audit lens asks for: the signature promises
control that does not exist. VERIFIED.

**binding_health.py:72-76, 90-114, 223 — `silence.replace_retry`'s return value is discarded at every call site in this module, unlike several sibling modules.**

`_land` never checks `silence.replace_retry`'s return. `silence.replace_retry`'s own docstring
(src/silence.py:263-280) is explicit: it returns `True`/`False`, and on persistent
`PermissionError` it returns `False` without raising — "persistent denial is recorded, never
raised — the caller's write lands next round." That contract requires the *caller* to know the
write didn't land so it can react (retry, refuse to proceed, or at least not report success).
`foreman.py`, `completeness.py`, `health.py`, `pipeline.py`, `runguard.py`, and `pick_model.py`
all check this return value (`if not silence.replace_retry(...)` or equivalent — confirmed by
grep across `src/`). `binding_health.py` does not: `quarantine()` returns `q[host]` and fires the
SUPERVISOR escalation regardless of whether `_land` actually persisted the quarantine record;
`release()` returns its `why` string regardless of whether the un-quarantine persisted. On a
Windows `PermissionError` collision (the exact scenario `replace_retry`'s docstring names, and
which this project has hit before — "One such collision took an assay worker down mid-batch,
2026-08-23, WinError 5"), a host could be reported as quarantined/released in this run's console
output and to the SUPERVISOR channel while the on-disk `HOST_QUARANTINE.json` silently keeps the
old state. Self-heals next run per the project's stated design, but the discrepancy between
in-memory return value and on-disk truth is unobserved here where several siblings do observe it.
VERIFIED.

---

## MINOR

**binding_health.py:61-69 — `_load` collapses a corrupted `HOST_QUARANTINE.json` to `{}` (empty), which is fail-OPEN for a trust-state file, contradicting this project's own FAIL CLOSED rule (CLAUDE.md Hard Rule -1).**

A corrupt/unparseable `QUARANTINE` file hits the bare `except Exception: silence.note(...); return
default` path with `default={}`. Since `quarantined()` derives from this, every previously
quarantined host becomes indistinguishable from "never quarantined" — the file that exists to
say "do not trust this host yet" silently stops saying so on the exact kind of corruption CLAUDE.md
calls out by name ("a corrupt halt file: all refuse. Silence must never authorise anything").
Impact is bounded (a bad host will very likely just fail canary again on the next `run()` and get
requarantined) but it is inconsistent with the project's stated fail-closed posture for exactly
this class of file. VERIFIED.

**binding_health.py:199-203 — `run(limit=..., only=...)` truncates the host roster via `hosts[:limit]`.**

Judged per the audit brief's guidance: this is *not* the "known-present/known-absent identity
per host" fixture the module's docstring legitimately describes (that fixture is the two probes
inside `canary()`, unaffected by `limit`). `limit` instead slices the **roster of hosts to
check** — the ~200-host list itself. Read narrowly this is a debug/dry-run CLI flag
(`--limit`), off by default (`None` = uncapped), analogous to other modules' `--pilot N` flags,
and nothing in the codebase currently calls `run()` with a non-None `limit` (module is unwired —
see above). Flagging as MINOR/NOTE rather than BLOCKING because it is opt-in and currently
unreachable from any automated path, but it is worth the owner's attention before this module is
ever wired into a scheduled job: if a future caller defaults `limit` to some value "for speed,"
hosts past the cutoff would never be canaried and a rotted binding among them would be
silently indistinguishable from a healthy one — which is the exact failure this whole module
exists to prevent. SUSPECTED as a future risk, VERIFIED as present-tense inert.

**binding_health.py:131 — the 200-character threshold in `_probe_present` for "too thin to be the page" is an unexplained magic number.**

Not necessarily wrong, but no justification is given for 200 vs. any other value, and a
legitimately short-but-real stub article could false-fail the present-probe, quarantining a
genuinely healthy host. Low confidence this is a live problem (docstring doesn't discuss stub
articles), flagged as NOTE-level. SUSPECTED.

---

## NOTE

- `known_present_title` (binding_health.py:167-193) is correctly uncapped: it scans every
  `data/records/*.json` file until it finds a matching source's first sufficiently-long entry
  name, with no early cutoff on the number of records or entries scanned. Not a Hard-Rule-0
  violation.
- `quarantine()`'s escalation call (binding_health.py:99-105) wraps `ESC.escalate(...)` in a
  bare `except Exception: silence.note(...)`. This mirrors the project's own established
  best-effort-notification idiom elsewhere (the recorder must never be what breaks the run) and
  is consistent with `silence.py`'s own philosophy — not flagging as a defect, just noting it was
  checked against the escalation-chain hard rule and found consistent with it.
- `canary()`'s `reason` field (binding_health.py:162-164) only reports the present-probe's
  failure detail when both probes fail simultaneously — cosmetic information loss, not a
  correctness bug.

---

## Summary for the record() call

Two BLOCKING structural defects (absent-probe exception-swallowing that can bless a rotted
binding; hand-rolled tmp-file naming reproducing the project's own named worst recurring defect)
plus a third BLOCKING concurrency race matching a previously-fixed defect class in
`sweep_plan.py`, two MAJOR findings (dead `timeout` parameter; discarded `replace_retry` return
unlike sibling modules), plus MINOR/NOTE items. **The module is confirmed NOT wired into any
caller in `src/`** — its quarantine mechanism currently affects nothing downstream.
