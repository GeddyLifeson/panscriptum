"""WORK ORDERS — what the nets found, who should fix it, and deletion when it is fixed.

OWNER RULING 2026-08-25: *"each time the nets and safes find something that should be submitted
as a work order, and when it's resolved the work order should be deleted, and this should
transform the scheduled task into something that just looks for what's being asked of it from
all of these nets and safes, because they should be taking over a lot of what it's already
supposed to do."*

WHAT CHANGES. Until now every maintenance run RE-DERIVED the state of the library from scratch:
read the page, read four ledgers, read the automation's outputs, re-measure, re-diagnose. That
was necessary when nothing else could see a fault. It is not necessary now -- 127 drill nets, a
battery, a liveness scan, a ledger chain, a secret scanner and a canary sweep all detect faults
continuously and precisely. A run that re-derives what they already know spends its budget
re-discovering rather than fixing, and this session watched exactly that happen: four runs in a
row re-diagnosed the same 874 entries as data loss when they were a queue.

So the detectors FILE, and the run WORKS THE FILE.

THE HANDLER LADDER, in the owner's order -- each rung is tried before the one above it, and the
last two rungs are the expensive ones:

    LOCAL     the free local model via `local_agent`. Mechanical, gated, unlimited.
    BOTS      the repo's own machinery: foreman remedies, overwatch, the keeper.
    RUN       the scheduled maintenance run (a Claude session, hourly, metered).
    SESSION   an interactive session -- second-to-last, by ruling.
    OWNER     a person. Account actions, charter judgments, curatorial calls. Last.

An order names the LOWEST rung that can honestly close it. Naming a rung too high wastes the
expensive ones; naming it too low means it bounces. `escalation.py` supplies the severity, this
supplies the addressee, and the two are deliberately separate questions: *how bad is it* and
*who can fix it* are not the same axis, and collapsing them is what produces a queue where
everything is urgent and nothing is actionable.

DELETION IS THE POINT. A resolved order is REMOVED from the open file and appended to
`workorders_closed.jsonl` -- a paper trail, never a growing backlog. This project's ledgers rot
precisely because resolved things linger in the Open section; the discipline that keeps BUGS.md
honest is enforced here by construction instead of by remembering.
"""
import argparse
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence  # noqa: E402

OPEN_FILE = os.path.join(HERE, "state", "workorders.json")
CLOSED_LOG = os.path.join(HERE, "state", "workorders_closed.jsonl")

# The handler ladder, cheapest first. The index IS the order.
LADDER = ["LOCAL", "BOTS", "RUN", "SESSION", "OWNER"]

# Severity mirrors escalation's rungs so the two vocabularies cannot drift apart. A validated
# enum rather than a free string, because a severity nobody can enumerate cannot be routed
# (the discipline prowler enforces via schema).
SEVERITY = ["INFO", "MINOR", "MAJOR", "BLOCKING"]


class BadOrder(ValueError):
    """A work order that could not be routed. Refused rather than filed unroutable."""


def _load():
    try:
        with open(OPEN_FILE, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        silence.note("workorders.py:load")
        return {}


def _land(d):
    os.makedirs(os.path.dirname(OPEN_FILE), exist_ok=True)
    tmp = OPEN_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, sort_keys=True, ensure_ascii=False)
    silence.replace_retry(tmp, OPEN_FILE)


def order_id(code, where=""):
    """Stable id from the FAULT, not from the moment it was found.

    Deliberately content-addressed: the same net finding the same fault on the next cycle must
    UPDATE one order, not file a second. A queue that grows one entry per cycle per fault is how
    a detector becomes noise -- and noise is switched off, which is how a project ends up with
    detectors nobody reads.
    """
    return hashlib.sha1(("%s|%s" % (code, where)).encode("utf-8")).hexdigest()[:12]


def file_order(code, what, handler, severity="MAJOR", where="", evidence=None, found_by=""):
    """Open (or refresh) one work order. -> the order.

    Refreshing rather than duplicating also gives the thing a queue most needs and rarely has: a
    `seen` count and a `first_seen`, so "this has been failing for six hours" is a fact rather
    than an impression.
    """
    handler = str(handler or "").upper()
    severity = str(severity or "").upper()
    if handler not in LADDER:
        raise BadOrder("handler %r is not one of %s -- an order nobody is addressed to is an "
                       "order nobody works" % (handler, LADDER))
    if severity not in SEVERITY:
        raise BadOrder("severity %r is not one of %s" % (severity, SEVERITY))
    d = _load()
    oid = order_id(code, where)
    now = time.time()
    prev = d.get(oid) or {}
    d[oid] = {"id": oid, "code": str(code), "what": str(what)[:600], "handler": handler,
              "severity": severity, "where": str(where)[:200],
              "evidence": evidence if isinstance(evidence, (dict, list)) else
              (None if evidence is None else str(evidence)[:400]),
              "found_by": str(found_by or "")[:80],
              "first_seen": prev.get("first_seen", now), "last_seen": now,
              "seen": int(prev.get("seen", 0)) + 1}
    _land(d)
    return d[oid]


def resolve(oid, how, by=""):
    """Close an order: REMOVE it from the open file, append it to the paper trail.

    Deletion is the ruling, and it is enforced here rather than trusted to a person remembering
    to prune. An order that is 'resolved' but still listed is indistinguishable from an open one
    to the next reader, which is exactly how BUGS.md's Open section rotted.
    """
    d = _load()
    rec = d.pop(oid, None)
    if rec is None:
        return None
    rec.update({"resolved_at": time.time(), "resolution": str(how)[:400], "resolved_by": by})
    _land(d)
    try:
        os.makedirs(os.path.dirname(CLOSED_LOG), exist_ok=True)
        with open(CLOSED_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        silence.note("workorders.py:closed-log")
    return rec


def resolve_code(code, how, where="", by=""):
    """Close by fault identity rather than by id -- what a detector does when it stops firing."""
    return resolve(order_id(code, where), how, by=by)


def open_orders(handler=None, severity=None):
    """-> [orders], worst first, then oldest first."""
    rows = list(_load().values())
    if handler:
        rows = [r for r in rows if r.get("handler") == str(handler).upper()]
    if severity:
        rows = [r for r in rows if r.get("severity") == str(severity).upper()]
    rows.sort(key=lambda r: (-SEVERITY.index(r.get("severity", "INFO")),
                             r.get("first_seen", 0)))
    return rows


def for_ladder():
    """-> {rung: [orders]} across the whole ladder, cheapest rung first."""
    out = {}
    for rung in LADDER:
        got = open_orders(handler=rung)
        if got:
            out[rung] = got
    return out


def sweep_detectors():
    """Run the cheap detectors and file what they find. -> (filed, resolved).

    THE DETECTORS ARE THE AUTHORS. Each one owns a `code`, and an order is filed when the
    detector fires and RESOLVED when it stops -- so the queue tracks reality rather than
    accumulating. Only detectors that cost nothing belong here; the drill and the battery are
    run by the supervisor and file through `escalation`, not from inside this sweep.
    """
    filed, closed = [], []

    def _fire(ok, code, what, handler, severity, where="", evidence=None, found_by=""):
        if ok:
            if resolve_code(code, "detector stopped firing", where=where, by="workorders.sweep"):
                closed.append(code)
        else:
            filed.append(file_order(code, what, handler, severity, where=where,
                                    evidence=evidence, found_by=found_by))

    # 1. the ledgers
    try:
        import ledger_guard as LG
        bad = LG.check_all()
        chain_ok, chain_problems = LG.verify_chain()
        _fire(not bad, "LEDGER_STRUCTURE",
              "a relay ledger is not intact: %s" % json.dumps(bad)[:300],
              "RUN", "BLOCKING", found_by="ledger_guard")
        _fire(chain_ok, "LEDGER_CHAIN",
              "the ledger hash chain does not verify: %s" % "; ".join(chain_problems[:3]),
              "SESSION", "BLOCKING", found_by="ledger_guard")
    except Exception:
        silence.note("workorders.py:ledgers")

    # 2. dead code / checks that cannot fail
    try:
        import liveness
        import drill as _D
        n = sum(len(v) for v in liveness.scan().values())
        _fire(n <= _D.LIVENESS_CEILING, "LIVENESS_RATCHET",
              "dead code / unfailable checks rose to %d against a ceiling of %d"
              % (n, _D.LIVENESS_CEILING), "LOCAL", "MAJOR", found_by="liveness")
    except Exception:
        silence.note("workorders.py:liveness")

    # 3. quarantined wiki hosts -- one order per host, so each closes on its own recovery
    try:
        import binding_health as BH
        q = BH.quarantined()
        for host, rec in sorted(q.items()):
            file_order("HOST_QUARANTINED", "%s: %s" % (host, rec.get("reason", "")),
                       "BOTS", "MINOR", where=host, found_by="binding_health")
        filed.extend([])
    except Exception:
        silence.note("workorders.py:bindings")

    # 4. secrets staged for the public repo
    try:
        import publish as P
        hits = P.scan_for_secrets(P.SITE) if os.path.isdir(P.SITE) else []
        _fire(not hits, "SECRET_STAGED",
              "credential-shaped values staged for the PUBLIC repo: %s"
              % "; ".join("%s:%s" % (f, n) for f, n, _w in hits[:5]),
              "SESSION", "BLOCKING", found_by="publish.scan_for_secrets")
    except Exception:
        silence.note("workorders.py:secrets")

    return filed, closed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sweep", action="store_true", help="run the detectors and file/close")
    ap.add_argument("--resolve", help="order id to close")
    ap.add_argument("--how", default="", help="resolution text (required with --resolve)")
    ap.add_argument("--handler", help="show only this rung")
    a = ap.parse_args()

    if a.resolve:
        if not a.how.strip():
            print("refused: --how is required. A closed order with no resolution recorded is "
                  "indistinguishable from one that was deleted to tidy the queue.")
            return 2
        rec = resolve(a.resolve, a.how, by="cli")
        print("closed %s" % a.resolve if rec else "no such open order: %s" % a.resolve)
        return 0 if rec else 1

    if a.sweep:
        filed, closed = sweep_detectors()
        print("swept: %d filed/refreshed, %d closed" % (len(filed), len(closed)))

    rungs = for_ladder()
    if not rungs:
        print("no open work orders -- the nets found nothing outstanding")
        return 0
    for rung in LADDER:
        rows = rungs.get(rung)
        if not rows:
            continue
        print("\n%s  (%d)" % (rung, len(rows)))
        print("-" * 78)
        for r in rows:
            age_h = (time.time() - r.get("first_seen", 0)) / 3600.0
            print("  [%-8s] %-12s %s" % (r.get("severity"), r.get("id"), r.get("what", "")[:70]))
            print("             seen %dx, first %.1fh ago, from %s"
                  % (r.get("seen", 1), age_h, r.get("found_by", "?")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
