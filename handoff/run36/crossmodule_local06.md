# Cross-module needs — LOCAL batch 6

## 0f8be4893543 (binding_health.py:242,287) — `timeout=25` is dead until feats.py accepts one

**Verified against current source** (both functions re-read fresh this shift, not from the
order's stale description): `_probe_present(host, title, timeout=25)` calls `_fetch_chars(host,
t)`, which calls `feats.fetch(host, [title])`; `_probe_absent(host, timeout=25)` calls
`feats.fetch(host, [ABSENT_PROBE])` directly. Neither passes `timeout` anywhere. Confirmed no
caller anywhere in `src/` passes `timeout=` to either function (`grep -n "_probe_present\|
_probe_absent" src/*.py`), so the parameter is currently pure decoration — reads as a control,
controls nothing.

**Why this is not fixed in binding_health.py, and why removing the parameter is the wrong
call too:**

- The real bound has to land in `feats.py` (which I do not own this shift). `feats.api()` and
  `feats.fetch()` have no `timeout` parameter at all — every network call goes through
  `urllib.request.urlopen(req, timeout=TIMEOUT)` with `TIMEOUT` a **module-level constant** in
  `feats.py`. There is currently no way for a caller to bound an individual call shorter than
  that constant, so `_probe_present`/`_probe_absent` cannot honour a per-call `timeout` without
  `feats.py` growing one.
- Removing the parameter instead (since nothing calls it with a value) would be a signature
  break on the strength of a guess about what the order wants, which the run's own instructions
  rule out ("no signature breaks"). It would also foreclose the real fix, which is to wire it
  through once `feats.py` supports it.
- A binding_health-local workaround (e.g. running the fetch in a worker thread and abandoning it
  past `timeout`) was considered and rejected: `urllib`'s request would keep running in the
  background past the deadline (nothing here can cancel a socket read on another thread), which
  trades a hung caller for a leaked thread and an in-flight request nobody is tracking — a worse
  failure mode than the current one for a MINOR-severity finding, and out of proportion for a
  ~200-host canary that already runs off the hourly path.

**Suggested fix in `feats.py`** (not made here — outside my module list this shift):

```python
# feats.py
def api(host, params, retries=2, timeout=None):
    ...
    with urllib.request.urlopen(req, timeout=timeout or TIMEOUT) as r:
    ...

def fetch(host, titles, timeout=None):
    ...
    d = api(host, {...}, timeout=timeout)
    ...
```

Once that lands, `binding_health._fetch_chars(host, title, timeout=None)` and
`_probe_present`/`_probe_absent` can pass their own `timeout` argument straight through, and the
parameter stops being decorative. Left OPEN pending that change.
