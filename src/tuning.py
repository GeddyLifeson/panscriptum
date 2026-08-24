#!/usr/bin/env python3
"""TUNING — the settings that should never have been constants.

THE ASYMMETRY NOBODY ENCODED
----------------------------
Concurrency helps on cloud and HURTS on local, and every job in this library was written with a
single hardcoded worker count that assumed cloud.

    CLOUD   N workers hit N independent buckets. Doubling workers roughly doubles throughput
            until the buckets rate-limit, and a bucket that stalls costs only its own request.

    LOCAL   N workers hit ONE model on ONE card. They do not run concurrently; ollama queues
            them, each waits behind the others, and every one of them counts that wait against
            its own timeout. Past the point where the queue depth exceeds the timeout, adding a
            worker does not slow the run down -- it makes the run FAIL, because everything times
            out at once and nothing completes.

That is not a theory. Measured on this machine tonight: fourteen workers (chain 8, assay 6)
against one resident gemma3:12b produced HTTP 503 and a 393-entity assay batch that scored
exactly ZERO, while the same code with the pool up had scored seven. The workers were not slow.
They were strangling each other.

    entities read, pool degraded, 14 workers ....... 2.3 / hour
    calls/hour measured earlier with the pool up .. 940 / hour

A 400x spread across the same code, and the only thing the code did about it was keep using the
same worker count for both.

WHAT ELSE HAS TO MOVE WITH THE REGIME
-------------------------------------
Not just workers. Context is the other one: a cloud bucket carries 128k tokens and reads an
entity's whole record in one call, while the local window is 6,144 tokens and cannot. Chunk size,
per-call timeout, and whether an oversized unit is attempted at all are all functions of which
transport is carrying the run, and all of them were fixed numbers.

The regime is re-read on a timer rather than resolved once, because it CHANGES underneath a long
job -- buckets shed to HTTP 402 mid-run, and a run that started on cloud settings finishes on
local hardware still using them. That is precisely what happened to the 393-entity batch.
"""
import argparse
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

# How many answering cloud buckets it takes to call the regime CLOUD. Two is not enough: a pool
# that thin is one 402 away from being local, and a run configured for twelve workers against
# two buckets is the strangling case again with extra steps.
CLOUD_MIN_BUCKETS = 3
RECHECK_SECONDS = 180

PROFILES = {
    # workers        how many concurrent model callers
    # chunk          characters of source text per read call
    # timeout        seconds per call
    # max_prompt     None = no ceiling; else defer units larger than this rather than truncate
    # workers on cloud DERIVE from how many buckets actually answer (the proof), one worker
    # per answering lane plus slack, clamped 4..16. A constant 12 was wrong in both directions:
    # too many for a 4-bucket evening, too few for a 14-lane afternoon.
    "cloud": dict(workers=12, chunk=36000, timeout=180, max_prompt=None,
                  note="independent buckets; concurrency is free until they rate-limit"),
    "local": dict(workers=2, chunk=8000, timeout=420, max_prompt=20000,
                  note="one model on one card; workers queue behind each other"),
    "starved": dict(workers=1, chunk=6000, timeout=600, max_prompt=20000,
                    note="nothing is answering reliably; one caller, long patience"),
}

_CACHE = {"at": 0.0, "regime": None, "why": ""}


def _ollama_up(host="http://localhost:11434"):
    try:
        with urllib.request.urlopen(host + "/api/tags", timeout=6) as r:
            return r.status == 200
    except Exception:
        silence.note("tuning.py:ollama_up")
        return False


def _answering_buckets():
    """How many cloud buckets actually ANSWER -- from the proof, not from reported headroom.

    Headroom is not evidence: twenty-five of thirty-six buckets once reported healthy quota
    while answering nothing. POOL_PROOF.json is written by `cascade_bridge.prove()` and is the
    only honest count.
    """
    p = os.path.join(HERE, "data", "POOL_PROOF.json")
    try:
        age = time.time() - os.path.getmtime(p)
        with open(p, encoding="utf-8") as f:
            rows = json.load(f)
    except Exception:
        silence.note("tuning.py:pool_proof")
        return 0, "no pool proof on disk"
    n = sum(1 for r in rows if isinstance(r, dict) and r.get("verdict") == "answers")
    if age > 3600:
        # A stale proof is a claim about a pool that may no longer exist. Believe it, but say so.
        return n, "%d answering (proof is %.1fh old)" % (n, age / 3600)
    return n, "%d answering" % n


def regime(force=False):
    """'cloud' | 'local' | 'starved', re-read on a timer."""
    now = time.time()
    if not force and _CACHE["regime"] and now - _CACHE["at"] < RECHECK_SECONDS:
        return _CACHE["regime"]
    n, why = _answering_buckets()
    if n >= CLOUD_MIN_BUCKETS:
        r = "cloud"
    elif _ollama_up():
        r = "local"
        why += "; ollama up"
    else:
        r = "starved"
        why += "; ollama down"
    _CACHE.update({"at": now, "regime": r, "why": why})
    return r


def profile(force=False):
    r = regime(force=force)
    p = dict(PROFILES[r])
    if r == "cloud":
        n, _ = _answering_buckets()
        p["workers"] = max(4, min(16, n + 2))
    p["regime"] = r
    p["why"] = _CACHE["why"]
    return p


def workers(requested=None, force=False):
    """The worker count to actually use.

    A caller's request is treated as a CEILING, never a floor. A job asking for eight workers on
    local hardware is asking for the failure mode, and honouring that request politely is how
    the 393-entity batch scored zero.
    """
    p = profile(force=force)
    n = p["workers"]
    return min(requested, n) if requested else n


def main():
    ap = argparse.ArgumentParser(description="which regime is the machine in, and what follows")
    ap.add_argument("--force", action="store_true", help="ignore the cache")
    a = ap.parse_args()
    p = profile(force=a.force)
    print("regime      %s" % p["regime"])
    print("why         %s" % p["why"])
    print("")
    for k in ("workers", "chunk", "timeout", "max_prompt"):
        print("  %-12s %s" % (k, p[k]))
    print("")
    print("  " + p["note"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
