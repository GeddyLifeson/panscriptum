# Nets staged by batch 08 (run #36) — for the owner of `src/drill.py` / `src/verify_math.py`

Batch 08 may not edit `drill.py` or `verify_math.py` this shift, so the complete proposed nets
are written out here. Each one has been RUN in this form (as a standalone script against the
live modules) and reports the verdict shown.

---

## NET 1 — `drill.py`: a named ESTATE fault must be able to fail the sweep

**Why.** This is the defect order `5863bd9f566a` names, and it is the house's own worst shape:
`allsweep.main()` graded only `estate["artifacts"]["bad"]`, so `MASTER CHARTER MISSING`,
`CHARTER_SPINE_CODES.json MISSING`, `TERMINAL HAS NO HTML ENTRY POINT` and `OLLAMA UNREACHABLE`
could all be true at once and the sweep still printed `0 subsystem(s) in a bad state` and exited
0. Proven by execution before the fix. The fix must now be held by a net, because the thing that
regresses silently is a grade nobody watches fail.

**Verified verdict when run against the current tree: HELD.**

```python
def _a_named_estate_fault_can_fail_the_sweep():
    """A check that cannot fail looks exactly like a check that passed.

    `estate.charter()` driven against an EMPTY tree emits its loudest finding,
    `MASTER CHARTER MISSING`. Until run #36 that row was printed, landed in ALLSWEEP.json and
    summed by nothing: the grade read `estate["artifacts"]["bad"]` only. The net drives the
    real `estate` functions against a real empty directory -- no stub findings -- so it cannot
    pass by agreeing with a fixture.

    It also pins the other direction, which is the half that makes the first half useful: the
    LIVE tree's ordinary rows (`chapters written`, `disk free`, `charter erratum (open)`,
    `catalogued sources with NO charter spine code`) must NOT be graded faults. An auditor that
    reddens on a healthy machine trains its reader to scroll past it.
    """
    import tempfile
    import allsweep as A
    import estate as E

    empty = tempfile.mkdtemp(prefix="drill_estate_")
    keep = E.HERE
    try:
        E.HERE = empty
        blank = {"charter": E.charter(), "written": E.written(),
                 "terminal": E.terminal(), "external": []}
    finally:
        E.HERE = keep
    named = A.estate_faults(blank)
    catches = any(f["finding"] == "MASTER CHARTER MISSING" for f in named)

    # A row that will not say what it is must count as a fault: fail-closed on the undecided.
    keyless = A.estate_faults({"charter": [{"finding": "somebody added a row", "detail": ""}]})

    # And the live tree's healthy rows must stay green.
    live = {"charter": E.charter(), "written": E.written(), "terminal": E.terminal()}
    quiet = not any(f["finding"].startswith("charter erratum") or
                    f["finding"].startswith("catalogued sources with NO") or
                    f["finding"] in ("chapters written", "terminal", "sources on the roll")
                    for f in A.estate_faults(live))
    return catches and len(keyless) == 1 and quiet


net(a, "a named ESTATE fault can actually fail the sweep",
    _a_named_estate_fault_can_fail_the_sweep,
    "MASTER CHARTER MISSING stood in ALLSWEEP.json and graded 0 -- the tier could not fail")
```

---

## NET 2 — `drill.py`: the fandom reachability memo must be able to go stale

**Why.** Order `65bd015ec5d6`. `_FANDOM_V4_CACHE` had no TTL, and the standard's two real
production callers are `dashboard.py`'s `serve_forever()` process and `publish.py --loop` — both
long-lived, so the FIRST probe's answer was served for the life of the daemon. The standard
whose stated purpose is "notice an outage while it is happening" could not change its mind. The
existing net `_battery_asks_the_network_once` pins the memo; nothing pins its expiry, and the
two requirements pull in opposite directions, which is exactly when both need holding.

**Verified verdict when run against the current tree: HELD.**

```python
def _the_network_memo_can_go_stale():
    """One answer per battery, and NOT one answer per daemon.

    Counts the PROBE, not the socket, so the net needs no network of its own and cannot pass
    merely because the machine happens to be offline. The memo is aged by hand rather than by
    sleeping -- a net that waits 300 seconds is a net that gets deleted.
    """
    import standards as ST
    calls = []
    saved_probe, saved_cache = ST._fandom_probe, dict(ST._FANDOM_V4_CACHE)
    try:
        ST._FANDOM_V4_CACHE.clear()
        ST._fandom_probe = lambda host, timeout, sk: (calls.append(host), (True, "up"))[1]
        ST.fandom_ipv4_reachable()
        key = list(ST._FANDOM_V4_CACHE)[0]
        at, val = ST._FANDOM_V4_CACHE[key]
        # Age it the way five minutes of serve_forever() would, then change the network under it.
        ST._FANDOM_V4_CACHE[key] = (at - 301.0, val)
        ST._fandom_probe = lambda host, timeout, sk: (calls.append(host), (False, "OUTAGE"))[1]
        after = ST.fandom_ipv4_reachable()
        expires = after == (False, "OUTAGE") and len(calls) == 2

        # ...and a caller that must know NOW can force it.
        calls.clear()
        ST.fandom_ipv4_reachable(ttl=0)
        forced = len(calls) == 1
    finally:
        ST._fandom_probe = saved_probe
        ST._FANDOM_V4_CACHE.clear()
        ST._FANDOM_V4_CACHE.update(saved_cache)
    return expires and forced


net(a, "the fandom reachability memo expires instead of freezing a daemon",
    _the_network_memo_can_go_stale,
    "an unexpirable memo made a long-lived dashboard report the first probe's answer for ever")
```

---

## NET 3 (proposed, and it is really a QUESTION) — `verify_math.py` §19r: exercise `embed_available`

**Why.** Order `c421410c2194`. `entity_match.embed_available()` has no caller anywhere in
`src/` — confirmed by `liveness.scan()` (it is the only `entity_match` row under `dead`) and by
grep. Its siblings `candidates`, `best`, `qualifier_compatible` and `similarity` are all
exercised by verify_math §19r; this one is skipped by the harness too.

**Verified verdict when run against the current tree: all four checks pass.**

**This net is staged but NOT recommended for adoption until the owner rules**, because the
function is documented deliberate design in two places (the module header's "WHY NO EMBEDDINGS
BY DEFAULT" and the function's own docstring: *"Nothing in this module calls it yet -- it is the
seam for an embedding pass, and it stays shut until an embedding model exists AND the exact join
has been exhausted"*). See the owner question in batch 08's report. If the ruling is **keep the
seam**, this net converts it from dead code into a proven contract; if the ruling is **remove
it**, the net is not needed and neither is the function.

```python
# verify_math §19r, appended. Drives the function with a STUBBED opener, never the live daemon:
# the assertion is about the SHAPE of the answer, and a check that needs Ollama up is a check
# that reports the machine's mood instead of the code's behaviour.
_em = _import("entity_match")

class _FakeTags:
    def __init__(self, body):
        self._body = body
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        return False
    def read(self):
        return self._body

def _with_tags(body):
    import urllib.request
    keep = urllib.request.urlopen
    try:
        urllib.request.urlopen = lambda url, timeout=None: _FakeTags(body)
        return _em.embed_available()
    finally:
        urllib.request.urlopen = keep

_no_model = _with_tags(b'{"models": [{"name": "qwen3:30b"}]}')
_has_model = _with_tags(b'{"models": [{"name": "nomic-embed-text:latest"}]}')

check("19r-embed-1", _no_model["available"] is False,
      "an installed model list with no embedding model reports available=False")
check("19r-embed-2", bool(_no_model["reason"]),
      "and it says WHY -- a reason code, not a silent null (this module's stated contract)")
check("19r-embed-3", _has_model["available"] is True and _has_model["models"],
      "an embedding model present reports available=True and names it")
check("19r-embed-4", _em.embed_available("http://127.0.0.1:1")["available"] is False,
      "an unreachable daemon degrades to available=False rather than raising")
```

Adopting this would also let `drill.LIVENESS_CEILING` fall by one more, since the function stops
reading as dead.
