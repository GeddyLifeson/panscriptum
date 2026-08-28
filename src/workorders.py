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


# --------------------------------------------------------------------- the battery's artifacts
#
# How long a battery result stays meaningful. A STALE result is a fault in its own right and is
# deliberately NOT treated as a pass: "nobody has run the battery since Tuesday" and "the battery
# is green" are different sentences, and a queue that cannot tell them apart reports the second
# when it means the first. Absence is handled the same way -- a missing artifact fires STALE,
# never silence.
PREFLIGHT_MAX_AGE = 6 * 3600
ALLSWEEP_MAX_AGE = 24 * 3600

# Every code this tier owns, each pinned to the `where` it files under. Named once so
# `sweep_detectors` can close each one when its detector goes quiet, rather than leaving orders
# that only ever accumulate.
#
# THE `where` IS PART OF THE FAULT'S IDENTITY: `resolve_code` closes `order_id(code, where)`, so
# a detector that files under one `where` and clears under another files an order it can never
# close. Written as a table rather than passed around precisely so the filing and the closing
# cannot disagree -- caught in review of this very function, which first took `where` from the
# live fault dict and therefore had nothing to pass when the fault went away.
BATTERY_WHERE = {
    "PREFLIGHT_PROBLEM": "health.preflight",
    "PREFLIGHT_STALE": "state/preflight_last.json",
    "BATTERY_GRADED": "allsweep",
    "BATTERY_STALE": "data/ALLSWEEP.json",
}
BATTERY_CODES = tuple(BATTERY_WHERE)


def battery_faults(preflight=None, allsweep=None, now=None):
    """PURE. Given the battery's two artifacts, -> {code: fault-dict or None}.

    WHY THIS EXISTS (run #33). `drill.py` escalated; nothing else in the battery did.
    `verify_math`, `health`, `allsweep` and `liveness` never called `escalate()` and were not in
    `sweep_detectors`, so a RED battery filed no work order at all. On 2026-08-25 the queue
    printed "nothing outstanding" while verify_math was FAILING its sweep-completeness check and
    the preflight was FAILING on a host whose every cached entry was empty. Both were found by a
    human reading console output -- which is precisely the re-derivation the owner's ruling was
    meant to end. A detector that reports only to a terminal is not a detector; it is a rumour.

    PURE ON PURPOSE, taking parsed artifacts rather than reading disk, so `drill.py` can attack
    it with a fabricated red battery and watch it file. A net that can only be tested by
    genuinely breaking the library is a net nobody ever tests.
    """
    now = time.time() if now is None else now
    out = {c: None for c in BATTERY_CODES}

    # ---- the preflight
    if not isinstance(preflight, dict):
        out["PREFLIGHT_STALE"] = {
            "what": "health.py --preflight has left no result: state/preflight_last.json is "
                    "missing or unreadable, so nothing knows whether the checks pass",
            "handler": "BOTS", "severity": "MAJOR"}
    else:
        age = now - float(preflight.get("at") or 0)
        if age > PREFLIGHT_MAX_AGE:
            out["PREFLIGHT_STALE"] = {
                "what": "the preflight result is %.1f hours old (ceiling %.0fh) -- stale is not "
                        "green" % (age / 3600.0, PREFLIGHT_MAX_AGE / 3600.0),
                "handler": "BOTS", "severity": "MINOR"}
        rows = preflight.get("rows") or []
        if rows:
            out["PREFLIGHT_PROBLEM"] = {
                "what": "health.py --preflight reports %d problem(s): %s"
                        % (len(rows), "; ".join("%s -> %s" % (r.get("what"), r.get("detail"))
                                                for r in rows[:3])),
                "handler": "RUN", "severity": "MAJOR", "evidence": rows[:20]}

    # ---- allsweep's GRADED tiers
    #
    # Tracks allsweep's own `bad` formula term for term -- imports, crashed/timed-out verifiers,
    # lint, bad estate artifacts, and the graded ESTATE findings -- because a queue that grades
    # differently from the sweep files orders for faults the sweep forgives and stays silent on
    # faults that fail it.
    #
    # THE TWO DID DRIFT, and saying they could not was the reason nobody looked (run #36).
    # allsweep gained an `estate_faults` term and this list did not, so `MASTER CHARTER MISSING`
    # FAILED THE BATTERY while filing NO WORK ORDER: the sweep graded it red and the queue
    # printed nothing outstanding. Mirroring is a thing that has to be re-established every time
    # either side changes, not a property a comment can assert.
    #
    # What protects it now is not this comment but the shape below: the estate term READS
    # allsweep's published `estate_faults` list rather than re-deriving which rows are faults.
    # The ONE severity judgement is made at the `note()` call in `estate.py`, published by
    # `allsweep.estate_faults`, and consumed here -- so a new ESTATE tier arrives here already
    # graded, and there is no second rule to keep in step. The remaining terms are still
    # hand-mirrored and are still a place drift can happen.
    #
    # `reconcile` is excluded here for the reason allsweep excludes it: its rows carry no
    # severity and are not all faults. Summing them made a green machine report sixteen broken
    # subsystems in run #26.
    if not isinstance(allsweep, dict):
        out["BATTERY_STALE"] = {
            "what": "allsweep has left no result: data/ALLSWEEP.json is missing or unreadable",
            "handler": "BOTS", "severity": "MAJOR"}
    else:
        at = allsweep.get("at")
        if at is None:
            # allsweep does not stamp a time inside the file; fall back to the caller's, and if
            # the caller could not supply one, say so rather than assuming freshness.
            at = allsweep.get("_mtime")
        age = None if at is None else now - float(at)
        if age is None or age > ALLSWEEP_MAX_AGE:
            out["BATTERY_STALE"] = {
                "what": ("allsweep's result carries no timestamp" if age is None else
                         "the allsweep result is %.1f hours old (ceiling %.0fh) -- stale is not "
                         "green" % (age / 3600.0, ALLSWEEP_MAX_AGE / 3600.0)),
                "handler": "BOTS", "severity": "MINOR"}
        bad = []
        for r in (allsweep.get("imports") or []):
            if not r.get("ok"):
                bad.append("import %s: %s" % (r.get("module"), str(r.get("detail"))[:160]))
        for r in (allsweep.get("verifiers") or []):
            if r.get("crashed") or r.get("timeout"):
                bad.append("verifier %s %s" % (r.get("check"),
                                               "timed out" if r.get("timeout") else "crashed"))
        for ln in (allsweep.get("lint") or []):
            bad.append("lint %s" % str(ln)[:160])
        for art in (((allsweep.get("estate") or {}).get("artifacts") or {}).get("bad") or []):
            bad.append("estate artifact %s" % str(art)[:160])
        # The four named ESTATE tiers, already graded by `allsweep.estate_faults`. Read, never
        # re-graded: `_row_is_fault` lives in allsweep and a copy of it here would be the second
        # rule this section exists to avoid.
        est = allsweep.get("estate")
        faults = allsweep.get("estate_faults")
        if faults is None and isinstance(est, dict) and any(
                k in est for k in ("charter", "written", "terminal", "external")):
            # FAIL-CLOSED on a report that ran the ESTATE tiers and published no grading: it
            # predates `estate_faults`, so an unknown number of its findings are unreadable
            # here. Scoring that silence as zero faults is the exact hole this term closes.
            bad.append("estate findings ungraded: this ALLSWEEP.json ran the ESTATE tiers but "
                       "carries no `estate_faults` key, so its findings cannot be counted")
        for f in (faults or []):
            if isinstance(f, dict):
                bad.append("estate %s: %s -- %s" % (f.get("tier"), f.get("finding"),
                                                    str(f.get("detail"))[:120]))
            else:
                bad.append("estate finding %s" % str(f)[:160])
        if bad:
            out["BATTERY_GRADED"] = {
                "what": "allsweep grades %d subsystem(s) bad: %s"
                        % (len(bad), "; ".join(bad[:3])),
                "handler": "RUN", "severity": "MAJOR", "evidence": bad[:20]}
    return out


def _load(with_digest=False):
    """The open queue. -> {id: order}, or ({id: order}, digest) when the caller intends to write.

    The digest is read BEFORE the file, never after, so it describes the copy the caller is
    about to modify. Reading it afterwards would be a race with no CAS at all: another writer
    landing in between would leave a digest that matches the file we did not read.
    """
    digest = silence.digest_of(OPEN_FILE) if with_digest else None
    try:
        with open(OPEN_FILE, encoding="utf-8") as f:
            d = json.load(f)
        d = d if isinstance(d, dict) else {}
    except FileNotFoundError:
        d = {}
    except Exception:
        silence.note("workorders.py:load")
        d = {}
    return (d, digest) if with_digest else d


def _mutate(change, attempts=8):
    """Read-modify-write the queue under COMPARE-AND-SWAP. -> (landed, value from `change`).

    WHY THIS IS NOT A PLAIN WRITE, and it was one until run #34 watched it fail. `file_order`
    and `resolve` were unlocked read-modify-writes over the whole queue landing through a single
    FIXED temp name (`workorders.json.tmp`) -- both halves of the hazard `silence.write_json`'s
    own docstring documents. Under twelve agents working the queue concurrently, a `--resolve`
    reported "no such open order" for an id demonstrably in the file and succeeded on retry: a
    sibling had landed a snapshot taken before that order existed.

    The retry is not the interesting part. The SILENCE is. A lost close silently REOPENS work
    that was actually done -- the order reappears and the next run redoes it -- and a lost file
    silently DROPS a finding a detector paid to make. Neither shows up anywhere: the write
    succeeds, it just writes the wrong thing. That is this project's signature failure, and the
    queue that tracks it was the last place still exposed to it.

    So the whole read-modify-write retries against a digest taken at read time, exactly as
    `runguard.claim()` was given the same treatment on the same day. A caller whose change is
    refused for staleness re-reads and re-applies it against the fresh copy, which is why
    `change` must be a pure function of the dict it is handed and must not have side effects of
    its own -- `resolve` appends to the paper trail only AFTER this returns landed.
    """
    import time as _t
    os.makedirs(os.path.dirname(OPEN_FILE), exist_ok=True)
    last_why = "not attempted"
    for a in range(attempts):
        d, digest = _load(with_digest=True)
        value = change(d)
        tmp = "%s.%d.%d.tmp" % (OPEN_FILE, os.getpid(), a)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1, sort_keys=True, ensure_ascii=False)
        landed, why = silence.replace_if_unchanged(tmp, OPEN_FILE, digest)
        if landed:
            return True, value
        last_why = why          # KEPT, not discarded: it is the only account of why the write
        try:                    # was refused, and "stale" and "denied" want different responses
            os.remove(tmp)      # from whoever reads the failure. Binding it and dropping it was
        except OSError:         # the swallowed-reason shape this module's own detectors look for.
            pass
        _t.sleep(0.05 * (a + 1))
    # Never raises: a queue write that cannot land is recorded and reported to the caller, which
    # is the established behaviour for every shared write here. What must NOT happen is a caller
    # believing it landed.
    silence.note("workorders.py:queue-write-lost")
    sys.stderr.write("workorders: queue write lost after %d attempt(s); last refusal was: %s\n"
                     % (attempts, last_why))
    return False, None


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
    oid = order_id(code, where)
    now = time.time()

    def _change(d):
        # Pure in `d`: `_mutate` may hand this a FRESH copy and re-apply it after a stale-write
        # refusal, so `seen` and `first_seen` must be re-derived from whatever copy arrives --
        # not captured once from the first read. That is the whole point of re-applying rather
        # than retrying the write: a concurrent refresh of the same fault is not lost.
        prev = d.get(oid) or {}
        d[oid] = {"id": oid, "code": str(code), "what": str(what)[:600], "handler": handler,
                  "severity": severity, "where": str(where)[:200],
                  "evidence": evidence if isinstance(evidence, (dict, list)) else
                  (None if evidence is None else str(evidence)[:400]),
                  "found_by": str(found_by or "")[:80],
                  "first_seen": prev.get("first_seen", now), "last_seen": now,
                  "seen": int(prev.get("seen", 0)) + 1}
        return d[oid]

    landed, rec = _mutate(_change)
    if not landed:
        # A finding that did not reach the queue must not be reported as filed. The caller
        # decides what to do about it; what it may not do is believe the order exists.
        sys.stderr.write("workorders: ORDER NOT FILED (%s) -- the queue write did not land after "
                         "retries; this finding is NOT in state/workorders.json\n" % code)
        return None
    return rec


def resolve(oid, how, by=""):
    """Close an order: REMOVE it from the open file, append it to the paper trail.

    Deletion is the ruling, and it is enforced here rather than trusted to a person remembering
    to prune. An order that is 'resolved' but still listed is indistinguishable from an open one
    to the next reader, which is exactly how BUGS.md's Open section rotted.

    AND THE RESOLUTION IS DEMANDED HERE, not only at the CLI. `main()` already refused an empty
    `--how` with the right sentence, while the function that actually does the deleting accepted
    `""` and `None` and wrote the string "None" into the paper trail. An invariant enforced in
    one caller is not an invariant; it is a habit that caller happens to have.
    """
    how = str(how or "").strip()
    if not how:
        raise BadOrder("a resolution is required to close %s. A closed order with no resolution "
                       "recorded is indistinguishable from one deleted to tidy the queue, and "
                       "the paper trail is the whole reason deleting it is safe." % oid)
    def _change(d):
        rec = d.pop(oid, None)
        if rec is not None:
            rec.update({"resolved_at": time.time(), "resolution": how[:400], "resolved_by": by})
        return rec

    # THE ORDER OF THESE TWO TESTS IS THE WHOLE POINT, and getting it backwards undid the fix it
    # was part of. `_mutate` returns `(False, None)` when the write could not land, so testing
    # `rec is None` FIRST swallows that case and returns the same None as "no such open order" --
    # and `main()` then prints exactly the "no such open order" sentence that today's CAS work
    # was done to stop a lost write from producing. A caller cannot tell "already closed" from
    # "your close was lost" if both come back the same way. So: DID IT LAND, then DID IT EXIST.
    landed, rec = _mutate(_change)
    if not landed:
        sys.stderr.write("workorders: ORDER NOT CLOSED (%s) -- the queue write did not land after "
                         "retries. The order is STILL OPEN and NOT in the paper trail. This is "
                         "not 'no such order'; it is a close that was lost.\n" % oid)
        return None
    if rec is None:
        return None                          # genuinely not open: nothing to close, nothing lost
    # THE PAPER TRAIL IS APPENDED ONLY AFTER THE DELETION LANDS. Appending first would write a
    # closed-log entry for an order still sitting open -- the two files would disagree, and the
    # closed log is what the next run trusts when it reconciles them.
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


# The two codes a settled identity verdict can be filed under. A host has ONE identity, so at
# most one of these may stand open against it at a time -- see `_supersede_binding_suspect`.
BINDING_DECIDED_CODE = {"CONFIRMED": "BINDING_RIGHT_ENTRY_NAMES_ARE_NOT_TITLES",
                        "MISBOUND": "BINDING_HOST_SERVES_ANOTHER_WIKI"}


def _supersede_binding_suspect(host, call, closed):
    """The orders this verdict REPLACES are closed: the undecided one, and the sibling verdict.

    Without this the split below only ever adds: the host is still `healthy is None`, so it
    still appears in `suspect` every sweep, and the vague BOTS order would sit open beside the
    precise OWNER one describing the same host for ever. Superseding is a real resolution --
    the question the old order asked has been answered -- so it is recorded as one rather than
    deleted quietly.

    AND THE SIBLING VERDICT IS SUPERSEDED TOO (order ebecc3cc19a7). This used to close only
    BINDING_SUSPECT, which is right exactly once: the first time a host's identity settles.
    When `binding_health` re-probes a host and the verdict FLIPS -- CONFIRMED to MISBOUND, or
    back -- the new code is filed at the same `where=host` and the OLD decided code is left
    standing, with no path anywhere that closes it: `_supersede` never named it, and the
    recovery sweep below only closes hosts that have recovered. The queue would then assert
    both "this IS the wiki it is bound to" and "this host serves another wiki" about one host,
    for ever, and the stale half is the one nobody can tell is stale. A host has one identity;
    the verdict that is no longer current is closed by the one that replaced it.
    """
    superseded = [("BINDING_SUSPECT",
                   "superseded: the host's identity was measured and the verdict is %s, so "
                   "this is filed under the code for that case instead of as an undecided "
                   "suspicion" % call)]
    # Only a DECIDED verdict may supersede the other decided one. An undecided call ("I could
    # not tell") answers nothing and must not close either finding -- that would be the same
    # silence-as-answer this whole split was built to stop.
    for verdict, code in (BINDING_DECIDED_CODE.items() if call in BINDING_DECIDED_CODE else ()):
        if verdict != call:
            superseded.append((code,
                               "superseded: this host's identity verdict has since changed to "
                               "%s, which is filed under its own code. A host has one identity, "
                               "so the earlier %s finding no longer describes it."
                               % (call, verdict)))
    for code, how in superseded:
        if resolve_code(code, how, where=host, by="workorders.sweep"):
            closed.append(code + ":" + host)


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

    # A DETECTOR THAT THROWS MUST FILE, NOT WHISPER (run #33). Every section below is wrapped so
    # that one broken detector cannot take the whole sweep down with it -- but the wrapper's
    # entire answer used to be `silence.note(...)`, which bumps a class-name counter in
    # state/failures.json that nobody on the handler ladder is described as reading. A
    # `LG.check_all()` that RAISES on a ledger too corrupt to parse is a worse condition than one
    # that returns problems, and it filed nothing at all: `_fire` was never reached, so that
    # detector's area of the queue read exactly like an area with nothing wrong in it. The note
    # still happens; the failure now also files under its own code, keyed by `where` so each
    # section owns one order, and closes itself the moment the detector completes again -- this
    # queue is not allowed to become one that only grows.
    def _detector(tag, ok):
        if ok:
            if resolve_code("DETECTOR_FAILED", "the %s detector ran to completion again" % tag,
                            where=tag, by="workorders.sweep"):
                closed.append("DETECTOR_FAILED:" + tag)
            return
        silence.note("workorders.py:" + tag)
        try:
            exc = sys.exc_info()[1]
            filed.append(file_order(
                "DETECTOR_FAILED",
                "the %s detector raised instead of reporting: %s: %s. Nothing it watches filed "
                "an order this cycle, so that area of the queue is UNKNOWN, not clean."
                % (tag, type(exc).__name__, str(exc)[:160]),
                "RUN", "MAJOR", where=tag, found_by="workorders.sweep"))
        except Exception:
            silence.note("workorders.py:detector-file")

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
        _detector("ledgers", True)
    except Exception:
        _detector("ledgers", False)

    # 2. dead code / checks that cannot fail
    try:
        import liveness
        import drill as _D
        n = sum(len(v) for v in liveness.scan().values())
        _fire(n <= _D.LIVENESS_CEILING, "LIVENESS_RATCHET",
              "dead code / unfailable checks rose to %d against a ceiling of %d"
              % (n, _D.LIVENESS_CEILING), "LOCAL", "MAJOR", found_by="liveness")
        _detector("liveness", True)
    except Exception:
        _detector("liveness", False)

    # 3. quarantined wiki hosts -- one order per host, so each closes on its own recovery
    try:
        import binding_health as BH
        q = BH.quarantined()
        for host, rec in sorted(q.items()):
            filed.append(file_order("HOST_QUARANTINED", "%s: %s" % (host, rec.get("reason", "")),
                                    "BOTS", "MINOR", where=host, found_by="binding_health"))
        # AND CLOSE THE ONES THAT RECOVERED. The comment above promised "each closes on its own
        # recovery" and nothing ever did it: `filed.extend([])` was a no-op standing where the
        # close pass should have been, so a released host kept its order for ever. Run #33 made
        # that visible at scale -- a canary sweep quarantined 20 hosts, a fix to the probe
        # released 14 of them, and all 14 orders stayed open against hosts that were healthy
        # again. A queue that only grows is one people stop reading. Found by the run #33 sweep
        # (batch 16), which read the promise and the no-op sitting next to each other.
        for oid, o in list(_load().items()):
            if o.get("code") == "HOST_QUARANTINED" and o.get("where") not in q:
                if resolve(oid, "host is no longer quarantined", by="workorders.sweep"):
                    closed.append("HOST_QUARANTINED:" + str(o.get("where")))
        _detector("bindings", True)
    except Exception:
        _detector("bindings", False)

    # 3b. HOSTS THAT ARE UP BUT WHOSE TITLES DO NOT RESOLVE. Not a quarantine -- the host is
    #     serving -- so nothing above would ever file it, and until run #33 nothing did: the
    #     canary had no verdict for "the binding is wrong" and reported it as a dead host.
    #     Filed at BOTS because `hostcheck.py --repair` is the tool that re-probes a binding.
    try:
        import binding_health as BH2
        rec = {}
        try:
            with open(BH2.OUT, encoding="utf-8") as f:
                rec = json.load(f)
        except Exception:
            rec = {}
        suspect = [h for h in (rec.get("hosts") or [])
                   if h.get("healthy") is None and "no catalogued title resolved"
                   in str(h.get("reason") or "")]
        seen_hosts = set()
        for h in suspect:
            host = h.get("host") or "?"
            seen_hosts.add(host)
            # "MAY BE bound to the wrong wiki, OR its entry names may not be article titles"
            # used to be the whole order, filed at BOTS, for both cases at once. Three of the
            # five standing ones were the second case and are NOT REPAIRABLE BY ANYTHING --
            # eberron.fandom.com really is the Eberron Wiki, and its bound source's catalogued
            # entries are rules features no wiki has articles for -- so they re-filed at a bot
            # every sweep for ever. An order permanently addressed to a handler that cannot act
            # on it is how a real signal turns into furniture. `binding_health` now MEASURES
            # which case it is by reading the wiki's own sitename, so the two go to the two
            # different places they belong.
            # COUNTED, like every sibling section. This block's `file_order` results used to be
            # discarded, so `swept: N filed/refreshed` under-reported by exactly the number of
            # binding orders -- and the None a REFUSED queue write returns went the same way, so
            # a finding that never reached the file could not be told from one that did. Both
            # directions are the same fault: a sweep reporting on work it did not verify. The
            # `[f for f in filed if f]` at the end of this function drops the Nones.
            b = h.get("binding") or {}
            call = b.get("verdict")
            if call == "CONFIRMED":
                filed.append(file_order(
                    "BINDING_RIGHT_ENTRY_NAMES_ARE_NOT_TITLES",
                    "%s IS the wiki it is bound to -- it names itself %r, matching the bound "
                    "source %r -- but none of its catalogued titles resolve, so the entry "
                    "names are not article titles there. NOTHING IS BROKEN AND NO BOT CAN FIX "
                    "IT: the remedy is curatorial, either accept that this source is mined at "
                    "feature level and carries no per-entry articles, or re-catalogue its "
                    "entries under names that wiki actually uses. Mining continues either way."
                    % (host, b.get("sitename"), b.get("matched")),
                    "OWNER", "MINOR", where=host, evidence=b,
                    found_by="binding_health.identity"))
                _supersede_binding_suspect(host, call, closed)
            elif call == "MISBOUND":
                filed.append(file_order(
                    "BINDING_HOST_SERVES_ANOTHER_WIKI",
                    "%s is bound to %r but SERVES %r (name agreement %s%%). The catalogued "
                    "entry names may be perfectly good; the host is wrong. Rebinding or "
                    "unbinding a source is a curatorial call, so it is filed, not done."
                    % (host, b.get("matched"), b.get("sitename"), b.get("score")),
                    "OWNER", "MAJOR", where=host, evidence=b,
                    found_by="binding_health.identity"))
                _supersede_binding_suspect(host, call, closed)
            else:
                # UNCLASSIFIED, UNKNOWN, or a canary record written before identity probing
                # existed. Kept at the old code and the old rung, because "I could not tell"
                # must not be filed as either answer.
                filed.append(file_order(
                    "BINDING_SUSPECT",
                    "%s answers its API but none of its catalogued titles resolve, and "
                    "its identity could not be settled (%s). The source may be bound to "
                    "the wrong wiki, or its entry names may not be article titles there. "
                    "Mining continues; this is not a quarantine."
                    % (host, b.get("detail") or "no identity probe on this record"),
                    "BOTS", "MINOR", where=host, evidence=h.get("reason"),
                    found_by="binding_health.canary"))
        # Close the ones that have recovered, so this cannot become a queue that only grows.
        for h in (rec.get("hosts") or []):
            host = h.get("host") or ""
            if host and host not in seen_hosts and h.get("healthy") is True:
                # All three codes, not just the old one. A host that starts resolving its
                # titles again has answered every version of this question, and closing only
                # the code that happened to exist first would strand the other two open on a
                # host that is now demonstrably fine.
                for code in ("BINDING_SUSPECT", "BINDING_RIGHT_ENTRY_NAMES_ARE_NOT_TITLES",
                             "BINDING_HOST_SERVES_ANOTHER_WIKI"):
                    if resolve_code(code, "titles resolve again", where=host,
                                    by="workorders.sweep"):
                        closed.append(code + ":" + host)
        _detector("binding-suspect", True)
    except Exception:
        _detector("binding-suspect", False)

    # 4. secrets staged for the public repo
    try:
        import publish as P
        raw = P.scan_for_secrets(P.SITE) if os.path.isdir(P.SITE) else []
        # SUPPRESSED FINDINGS ARE REPORTED, NOT ACTIONED. `scan_for_secrets` deliberately still
        # lists a waived finding so the waiver stays auditable -- so a caller that treats every
        # returned row as a fault re-files a work order for something already ruled on, for ever.
        # The push filter already made this distinction; this one did not, and the queue showed
        # a BLOCKING order for six documented audit-report quotations.
        hits = [h for h in raw if not str(h[2]).startswith("SUPPRESSED")]
        _fire(not hits, "SECRET_STAGED",
              "credential-shaped values staged for the PUBLIC repo: %s"
              % "; ".join("%s:%s" % (f, n) for f, n, _w in hits[:5]),
              "SESSION", "BLOCKING", found_by="publish.scan_for_secrets")
        # The same fault filed by `publish.push` through the escalation chain, under its own code.
        if not hits:
            if resolve_code("SECRET_IN_EXPORT", "scanner is clean (suppressed findings excluded)",
                            by="workorders.sweep"):
                closed.append("SECRET_IN_EXPORT")
        _detector("secrets", True)
    except Exception:
        _detector("secrets", False)

    # 5. THE BATTERY. Cheap because it reads the artifacts the battery already leaves behind
    #    rather than re-running it -- two small JSON files, not the 100-second sweep. See
    #    `battery_faults` for why the battery was silent to this queue until run #33.
    try:
        def _read(path, stamp_mtime=False):
            try:
                with open(path, encoding="utf-8") as f:
                    got = json.load(f)
                if stamp_mtime and isinstance(got, dict) and got.get("at") is None:
                    got["_mtime"] = os.path.getmtime(path)
                return got
            except Exception:
                return None

        faults = battery_faults(
            preflight=_read(os.path.join(HERE, "state", "preflight_last.json")),
            allsweep=_read(os.path.join(HERE, "data", "ALLSWEEP.json"), stamp_mtime=True))
        for code in BATTERY_CODES:
            f = faults.get(code)
            _fire(f is None, code,
                  (f or {}).get("what", ""), (f or {}).get("handler", "RUN"),
                  (f or {}).get("severity", "MAJOR"), where=BATTERY_WHERE[code],
                  evidence=(f or {}).get("evidence"), found_by="battery")
        _detector("battery", True)
    except Exception:
        _detector("battery", False)

    # 6. ORDERS FILED BY THE ESCALATION CHAIN, closed when their detector is clean again.
    #
    # Everything above files from a detector it can also re-run. `escalate()` files too, and
    # those orders had NO path back to closed -- so a drill breach that was fixed minutes later
    # left a BLOCKING order standing for ever, and a queue that only grows is one people stop
    # reading. The drill is the authority on its own state, so ask it.
    try:
        drill_state = os.path.join(HERE, "state", "drill_last.json")
        try:
            with open(drill_state, encoding="utf-8") as f:
                last = json.load(f)
        except FileNotFoundError:
            # The drill has simply never run in this tree. Nothing to close and nothing broken,
            # and it is kept distinct from a detector fault on purpose: a fresh clone must not
            # file a MAJOR order against an absence that is only the starting state.
            last = None
        if last is not None and not (last.get("breached") or []):
            if resolve_code("DRILL_BREACH", "drill re-runs clean: %s/%s nets held"
                            % (last.get("held"), last.get("nets")), by="workorders.sweep"):
                closed.append("DRILL_BREACH")
        _detector("drill-close", True)
    except Exception:
        _detector("drill-close", False)

    # `file_order` returns None for a finding whose queue write did not land (it says so on
    # stderr). Those must not be counted as filed -- "swept: N filed" over an order that is not
    # in the file is the same lie as a green check that never ran.
    return [f for f in filed if f], closed


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
