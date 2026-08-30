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

# Past this age a pool proof is annotated as stale but still counted at full strength. Named
# rather than inlined because this file's whole premise is that the numbers deciding behaviour
# should be visible and arguable, and a bare `3600` buried in a branch is neither. Whether a
# stale proof should be DISCOUNTED rather than merely captioned is a live question (m59: even a
# FRESH proof once certified 4-of-36 while live calls succeeded at 2.8%) and is not settled here.
PROOF_STALE_SECONDS = 3600

# THE SECOND HALF OF "CLOUD": not just that buckets answer a proof, but that calls SUCCEED.
#
# This is the project's most-repeated defect, and this is the site it was first named at. A
# bucket answering a proof call certifies REACHABILITY. Sizing every job in the kit from that
# certifies CAPACITY -- a different claim. Measured 2026-08-24: `regime()` read "cloud" (four
# buckets answered) while the live cloud success rate was 4%, so `_gate()` opened to 16 and
# nearly every chunk fell through the ladder onto one card. 1,168 of 1,235 chunks were then
# handed to a GPU that could not serve them and were thrown away. The same mistake has now been
# found at four other sites (m59, M8, m66, and `foreman`'s catalogue gate).
#
# So the label now requires both: enough buckets answering AND a measured success rate at or
# above this floor. 35% rather than 50% deliberately -- this decides how WIDE to open, and the
# cost of reading "local" while the cloud is merely mediocre is a slower run, whereas the cost
# of reading "cloud" while it is failing is work destroyed.
CLOUD_MIN_SUCCESS = 0.35

# Below this many recorded calls the rate is noise and is not allowed to veto. A handful of
# failures during a provider blip must not flip the whole library to local.
MIN_CALLS_TO_JUDGE = 20

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

# `buckets` is cached ALONGSIDE the verdict, not re-read beside it. profile() used to call
# _answering_buckets() again, unconditionally and uncached, to size the cloud worker count -- so
# a label cached from a five-bucket reading could hand out max(4, min(16, 0 + 2)) = 4 workers
# against a POOL_PROOF.json that now says zero, with the label and the number coming from two
# moments up to RECHECK_SECONDS apart. In the one module whose premise is that the regime is
# re-read on a timer BECAUSE it changes underneath a long job, the two halves of the answer must
# come from the same reading. It also saves a file read per profile() call.
_CACHE = {"at": 0.0, "regime": None, "why": "", "buckets": 0}


def _ollama_host():
    """The host the LIBRARY talks to, not the one this module happened to assume.

    This probe hardcoded `http://localhost:11434` as a default and was called with no argument,
    while every other module in the kit -- `read`, `magnitude`, `local_agent`, `overnight`,
    `standards`, `pick_model`, `pipeline`, `ingest_doc` -- reads `ollama_host` from
    `config.yaml`. Latent today, because config.yaml names that same URL. The day the host moves,
    `regime()` would certify a local model at an address nobody calls: "starved" while Ollama is
    healthy, or "local" while it is unreachable. That is this project's most-repeated defect
    (M7, m59, M8, m66) in its cheapest possible form -- a check measuring a path its callers are
    not on -- so it is closed here rather than filed again. Falls back to the same literal.
    """
    try:
        import yaml
        cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8")) or {}
        return str(cfg.get("ollama_host") or "http://localhost:11434")
    except Exception:
        silence.note("tuning.py:ollama-host")
        return "http://localhost:11434"


def _ollama_up(host=None):
    try:
        host = host or _ollama_host()
        with urllib.request.urlopen(host.rstrip("/") + "/api/tags", timeout=6) as r:
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
    if age > PROOF_STALE_SECONDS:
        # A stale proof is a claim about a pool that may no longer exist. Believe it, but say so.
        return n, "%d answering (proof is %.1fh old)" % (n, age / 3600)
    return n, "%d answering" % n


def cloud_success_rate(minutes=15):
    """The pool's MEASURED success rate over the recent past: (rate, calls).

    Read from `state/cascade_scratch.db`'s `usage` table -- the router's own record of what
    actually happened, which is the same source the dashboard's throughput panel and the
    "calls that succeed" standard both use. Deliberately NOT a fresh probe: a probe measures
    whether a call can be made, and the whole point here is to measure whether calls are
    WORKING. `(None, 0)` means no evidence, which is never treated as a fault.
    """
    import sqlite3
    path = os.path.join(HERE, "state", "cascade_scratch.db")
    try:
        conn = sqlite3.connect(path, timeout=2.0)
        try:
            row = conn.execute(
                "select count(*), sum(outcome='ok') from usage where ts > ?",
                (time.time() - minutes * 60,)).fetchone()
        finally:
            conn.close()
        total = int((row or [0])[0] or 0)
        if not total:
            return None, 0
        return (int(row[1] or 0) / total), total
    except Exception:
        silence.note("tuning.py:cloud-success")
        return None, 0


def regime(force=False):
    """'cloud' | 'local' | 'starved', re-read on a timer.

    "Cloud" now means answering AND succeeding -- see CLOUD_MIN_SUCCESS. Reachability was never
    the question the callers of this function are asking.
    """
    now = time.time()
    if not force and _CACHE["regime"] and now - _CACHE["at"] < RECHECK_SECONDS:
        return _CACHE["regime"]
    n, why = _answering_buckets()
    rate, calls = cloud_success_rate()
    # A rate only gets a vote once there is enough of it to mean anything.
    judged = rate is not None and calls >= MIN_CALLS_TO_JUDGE
    if judged:
        why += "; %.0f%% ok over %d calls" % (rate * 100, calls)
    if n >= CLOUD_MIN_BUCKETS and (not judged or rate >= CLOUD_MIN_SUCCESS):
        r = "cloud"
    elif _ollama_up():
        r = "local"
        why += "; ollama up"
    else:
        r = "starved"
        why += "; ollama down"
    _CACHE.update({"at": now, "regime": r, "why": why, "buckets": n})
    return r


def profile(force=False):
    r = regime(force=force)
    p = dict(PROFILES[r])
    if r == "cloud":
        # The count that sizes the workers is the SAME reading that produced the label -- see
        # the note on _CACHE. regime() has just run or just served its cache, and either way it
        # left `buckets` holding the count that decided the verdict.
        p["workers"] = max(4, min(16, _CACHE["buckets"] + 2))
    p["regime"] = r
    p["why"] = _CACHE["why"]
    return p


def workers(requested=None, force=False):
    """The worker count to actually use.

    A caller's request is treated as a CEILING, never a floor. A job asking for eight workers on
    local hardware is asking for the failure mode, and honouring that request politely is how
    the 393-entity batch scored zero.

    ZERO IS A REQUEST, NOT AN ABSENCE. The test was `if requested`, so a caller asking for 0
    workers -- the one request that unambiguously means "run nothing here" -- fell through the
    falsy branch and received the FULL profile count instead. The ceiling promised one line
    above became a floor of `n` in the single case where the caller wanted none. No caller
    passes 0 today (chain.py, magnitude.py and read.py all pass a positive int), so this is
    dormant rather than live; it is fixed because a contract that inverts itself on a boundary
    value is exactly what the next caller will trust. `None` still means "no request" and
    still yields the profile count. Pinned by verify_math S19ac.
    """
    p = profile(force=force)
    n = p["workers"]
    return min(requested, n) if requested is not None else n


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
