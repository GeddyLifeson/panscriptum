# Cross-module needs — WAVE 2B (health.py, endpoint.py, hostcheck.py, completeness.py)

Repair agent owning `health.py`, `endpoint.py`, `hostcheck.py`, `completeness.py` on run #36.
Orders worked: `f46fbdf61e31`, `232b4f3ffc79`, `1f79b49a4df7`, `771fc3b0f517`, `300c8d62a250`.

Nothing below was fixed, because every item needs a module outside that list — or is an owner
ruling rather than a defect.

---

## 1. `health.py --preflight` reports 1 problem, and the cause is a LAPSED QUARANTINE, not a fault

**This is the one thing standing between the preflight and zero, and it is not in any of my four
modules.** Reported here because the run's exit criterion is "0 problems" and this cannot be met
from wave 2B.

```
  FAIL  caches empty in a way that means broken
          feats/www_dandwiki_com: all 200 sampled entries empty
```

**It is pre-existing, and the timestamps prove it.** `state/HOST_QUARANTINE.json` holds
`www.dandwiki.com` with `retry_after: 1787889807`. The sweep filed these five orders at
`first_seen: 1787889974` — **167 seconds AFTER that quarantine expired.** So the preflight was
already red when the orders were written, and no edit in wave 2B touches `data/feats/`,
`binding_health`, or the quarantine record.

**Proved by execution** that it is the ONLY problem. Re-running the preflight in a throwaway
process with `binding_health.quarantined` patched in memory to report the host as still
quarantined (nothing on disk touched, `stamp=False`):

```
  ok    control characters in source
  ok    context budget
  ok    API paths per host family
  ok    caches empty in a way that means broken
  ok    state consistency
problems with the lapsed quarantine counted as active: 0
```

**The actual shape, and it will recur every 24h.** `check_caches()` excuses a host only while
`binding_health.quarantined()` reports it ACTIVE, and that predicate is
`retry_after > now` with `RETRY_AFTER_S = 24 * 3600`. `www.dandwiki.com` answers HTTP 403 to
every anonymous client — a permanent condition, and `times: 5` on the record says it has been
re-quarantined five times already. So the quarantine lapses on its own 24h clock and is only
re-established when something next probes the host and fails. **In the window between the lapse
and the next probe, the preflight goes red on a fault that is already known, already held, and
has no action that could clear it** — which is exactly the "permanent red is how a preflight
stops being read" failure `check_caches()`'s own docstring (run #33) was written to prevent. The
run-#33 fix closed the always-red case and left this once-a-day flicker open.

**NOT FIXED, and deliberately not, on two grounds:**

- **It may be DELIBERATE DESIGN, so it is a question.** A lapsed quarantine genuinely does mean
  "nobody has confirmed this host is still broken", and re-checking it then is arguably the
  point of a TTL. Widening `check_caches()` to excuse EXPIRED quarantines too would weaken a
  live safety on the strength of my own reading — the exact act HARD RULE -1 names as the
  incident that produced the escalation chain.
- The remedies all live outside wave 2B: re-probing the host is `binding_health`'s job, and
  `feats.py:169` is the only non-drill caller of `BH.quarantine()`.

**For the owner / whoever holds `binding_health.py`:** the choice is between (a) a permanently
403 host earning a permanent record rather than a 24h-expiring one, (b) `check_caches()`
excusing a lapsed quarantine until the next probe re-rules on it, or (c) accepting a daily
flicker. I have no ruling and did not make one.

---

## 2. `completeness.py:181 category_size()` — dead, pre-existing, already inside the ratchet

`liveness.py` reports it as having no caller anywhere in `src/`, and this is **not a
regression**: `state/drill_last.json` records `"liveness": 34` and the count after all of wave
2B's edits is still exactly **34** (ceiling 41). It was already among those 34 before this
shift.

Left alone deliberately. Its docstring states the contract it is kept for — "`category_size`
stays as it was for every caller that only wants the number" — so it is a deliberately retained
public helper, which makes removing it a QUESTION and not a fix. Flagging it only so the next
sweep does not file it as new. No order exists for it.

---

## 3. Nothing else. No wave-2B fix needed a file outside the four modules.

All five orders were closed inside `health.py`, `endpoint.py`, `hostcheck.py` and
`completeness.py`. `silence.py` supplied every primitive used (`write_json`, `digest_of`,
`replace_if_unchanged`, `replace_retry`) and needed no change — the CAS idiom applied to
`endpoint._save` and `hostcheck._land_hosts` is the one `endpoint.register()`,
`binding_health._land_cas`, `scout._mutate` and `workorders._mutate` already use, not a second
convention.
