#!/usr/bin/env python3
"""
STANDARDS — what "working" means, in numbers, and a work order when it is not met.

THE OWNER'S BRIEF
-----------------
    "your overwatch should have a 'standards' section where it understands that things should be
     operating at some minimum level and if it isn't it reports that to you or ollama or wherever
     as a work order to get it fixed"

Exactly the missing piece. `overwatch` could already tell whether a module imports and whether
the model finds a defect in the code. Neither of those catches the failure this project actually
keeps having, which is a system that is running, importing, parsing, raising nothing -- and
performing at a tenth of what it should.

Every example of that today was invisible until somebody happened to look at a number:

    the reader ran on one GPU for a morning        every check passed, throughput was 4x low
    5,090 chunks were skipped and filed as read    no exception, progress line said 9.8/s
    six buckets sat pinned at 1 request a minute   "available", and the pool was 10x too small
    the pool answered 450 calls an hour            nothing anywhere said what it SHOULD answer

That last line is the whole point. There was no declared expectation, so there was nothing to
fall short OF. A number with no floor under it cannot be wrong.

HOW A STANDARD IS WRITTEN
-------------------------
Each one names a measurable quantity, a floor, and -- crucially -- WHAT TO DO when it is breached.
A breach that says "throughput is low" is a complaint; a breach that says "throughput is low,
check for buckets pinned at rpm 1 and clear their learned caps" is a work order, and the
difference is whether anyone can act on it without re-deriving the diagnosis.

The floors are deliberately generous. A standard that trips on a normal bad minute trains its
reader to ignore it, and an ignored instrument is worse than none -- this project has burned that
lesson twice already, on a preflight FAIL everybody scrolled past and an auditor that called an
empty log file corrupt.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")


def _s(name, holds, observed, floor, order, severity="medium"):
    return {"standard": name, "holds": bool(holds), "observed": observed, "floor": floor,
            "order": order, "severity": severity}


def check(state=None):
    """Measure every declared standard. Returns a list of verdicts, breaches included.

    `state` is the dashboard's own state dict, so the standards and the instrument panel can
    never disagree about what a number is -- they read the same one.
    """
    if state is None:
        import dashboard as D
        state = D.state()
    out = []

    # ---------------------------------------------------------------- throughput
    per_hour = (state.get("throughput") or {}).get("per_hour", 0)
    out.append(_s(
        "model calls per hour", per_hour >= MIN_CALLS_PER_HOUR, per_hour, MIN_CALLS_PER_HOUR,
        "The pool is answering far below capacity. In order: check `data/`-side buckets pinned "
        "at rpm 1 by a learned cap (clear `learned` in state/cascade_scratch.db, the router now "
        "floors this at 2 and expires it after 6h); check how many buckets report headroom in "
        "the dashboard's quota panel; check that read.py is reaching the GPU as capacity rather "
        "than as a last resort after a backoff ladder.",
        severity="high"))

    # ---------------------------------------------------------------- correctness of the read
    for job in (state.get("jobs") or []):
        if job["name"] != "corpus read":
            continue
        warn = job.get("warn") or ""
        out.append(_s(
            "chunks nobody answered", not warn, warn or "none", "none",
            "A passage was sent to every transport and none replied. The entity is NOT cached "
            "when this happens, so nothing is lost -- but it means the pool and the GPU declined "
            "together, which is a capacity problem, not a reading problem. Same diagnosis as the "
            "throughput standard.",
            severity="high"))
        rate = job["done"] / max(job["total"], 1)
        eta = job.get("eta_h", 0)
        out.append(_s(
            "corpus read finishes inside a day", eta <= MAX_ETA_HOURS, f"{eta:.1f}h",
            f"{MAX_ETA_HOURS}h",
            "At this rate the read does not finish overnight. The lever is providers, not code: "
            "count the buckets with headroom, and if the answer is small the honest fix is more "
            "free tiers or waiting for the daily windows to roll.",
            severity="medium" if rate > 0.02 else "high"))

    # ---------------------------------------------------------------- the code itself
    w = state.get("watch") or {}
    broken = w.get("broken") or []
    out.append(_s(
        "every module imports", not broken, len(broken), 0,
        "A module that will not import is a module nobody knows is broken -- `verify_math` sat "
        "dead for an unknown period and every number it checks was unverified for exactly that "
        "long. Run `python src/allsweep.py` and fix what the IMPORT tier names.",
        severity="high"))
    out.append(_s(
        "no high-severity findings open", w.get("high", 0) == 0, w.get("high", 0), 0,
        "The standing sweep believes some code does something other than what it says. Read "
        "WATCH.md, confirm or refute each one, and fix or retire it.",
        severity="medium"))

    # ---------------------------------------------------------------- the library's own state
    lib = state.get("library") or {}
    cov = lib.get("coverage") or {}
    if cov:
        age = cov.get("age_h", 99)
        out.append(_s(
            "coverage figures are current", age <= MAX_COVERAGE_AGE_H, f"{age:.1f}h",
            f"{MAX_COVERAGE_AGE_H}h",
            "The cited/settled percentages predate whatever has run since, so they understate "
            "the library. `coverage.py` runs at the end of each supervisor cycle; if it is "
            "stale, the cycle is not completing.",
            severity="low"))
    src = lib.get("sources") or {}
    if src.get("total"):
        frac = src.get("with_host", 0) / src["total"]
        out.append(_s(
            "sources with a reachable wiki", frac >= MIN_HOST_COVERAGE, f"{frac:.0%}",
            f"{MIN_HOST_COVERAGE:.0%}",
            "Sources without a host are uncitable by construction. Run "
            "`python src/hostcheck.py --adopt --go`, and for homebrew try D&D Wiki and the "
            "publisher's own site -- homebrew is inconsistent about where it lives.",
            severity="medium"))

    # ---------------------------------------------------------------- the machinery
    quotas = state.get("quotas") or []
    live = [q for q in quotas if q.get("unlimited") or q.get("worst", 0) > 0.05]
    out.append(_s(
        "buckets with headroom", len(live) >= MIN_LIVE_BUCKETS, len(live), MIN_LIVE_BUCKETS,
        "The pool has collapsed to a handful of providers. Check the quota panel for buckets "
        "reading `rpm 0/1` -- that is a learned cap, not a real one -- and for keys that have "
        "started returning 401 or 402.",
        severity="high"))

    return out


# The floors. Each is set where a breach means something is genuinely wrong rather than merely
# unlucky, because a standard that cries wolf gets ignored and an ignored standard is worse than
# no standard at all.
MIN_CALLS_PER_HOUR = 900      # measured healthy: 3,400/h. A third of that is a real fault.
MAX_ETA_HOURS = 24            # the read is meant to be an overnight job
MAX_COVERAGE_AGE_H = 6
MIN_HOST_COVERAGE = 0.80      # 178 of 210 today; below 80% something has un-assigned sources
MIN_LIVE_BUCKETS = 6


def work_orders(state=None):
    """Only the breaches, worst first — the thing a person or a model is meant to act on."""
    bad = [v for v in check(state) if not v["holds"]]
    rank = {"high": 0, "medium": 1, "low": 2}
    return sorted(bad, key=lambda v: rank.get(v["severity"], 3))


def report(state=None):
    rows = check(state)
    bad = [r for r in rows if not r["holds"]]
    lines = [f"{len(rows) - len(bad)}/{len(rows)} standards met"]
    for r in rows:
        mark = "ok  " if r["holds"] else "MISS"
        lines.append(f"  {mark}  {r['standard']:<38}{str(r['observed']):>12}   "
                     f"floor {r['floor']}")
    for r in sorted(bad, key=lambda v: v["severity"]):
        lines.append("")
        lines.append(f"WORK ORDER [{r['severity'].upper()}] — {r['standard']}")
        lines.append(f"  observed {r['observed']}, floor {r['floor']}")
        for chunk in _wrap(r["order"], 92):
            lines.append("  " + chunk)
    return "\n".join(lines)


def _wrap(text, width):
    words, line, out = text.split(), "", []
    for w in words:
        if len(line) + len(w) + 1 > width:
            out.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        out.append(line)
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser(description="what working means, in numbers")
    ap.add_argument("--json", action="store_true", help="emit the verdicts as JSON")
    a = ap.parse_args()
    if a.json:
        print(json.dumps(check(), indent=1))
        return 0
    print(report())
    return 1 if work_orders() else 0


if __name__ == "__main__":
    sys.exit(main())
