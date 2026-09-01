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
import collections
import hashlib
import json
import re
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence  # noqa: E402

OPEN_FILE = os.path.join(HERE, "state", "workorders.json")
CLOSED_LOG = os.path.join(HERE, "state", "workorders_closed.jsonl")

# WHERE A DETECTOR'S REHEARSAL OF ITSELF IS RECORDED, so that it is not recorded in the
# paper trail (order c24fcbb8a291, shape (a)). The drill and the local agent each file a
# real order and immediately close it, every battery run, to prove the queue accepts and
# releases one. That evidence is worth keeping -- a drill net nobody can prove executed is
# the exact fault this project cares most about -- but it is not history, and it was
# drowning the history. Measured 2026-08-29: eight ids were 49.0% of the trail. Measured
# again 2026-08-30, one day later: 1,852 of 2,960 rows, 62.6%. The honest fraction falls
# every day the battery runs, which is every day.
#
# It is not tidiness. Three of the eight are recorded at MAJOR on the RUN rung and their
# `what` reads "__drill_rung4__ stopped: drill probe" -- distinguishable from a real
# MANAGER-rung subsystem stop only by recognising the probe's name. Anybody asking "how
# often has a subsystem been stopped in this library" got 628 hits, and the one that
# matters (order 4e7f1e47d0a0, catalogue_web stopped for nulling synthesis blocks) was
# buried under rehearsals of itself.
#
# THE EXISTING ROWS ARE NOT REWRITTEN. The closed log is append-only history and editing it
# to look tidier is the one thing a paper trail must never allow. This changes where FUTURE
# rehearsals go; the 1,852 already written stay where they are, and `main()` says so.
SELFTEST_LOG = os.path.join(HERE, "state", "workorders_selftest.jsonl")

# The reserved subject convention the drill ALREADY keeps for its synthetic subsystems --
# `__drill__`, `__drill_rung4__`, `__drill_rung4b__`, `__drill_litter_probe__`. Marking on
# the SUBJECT rather than on a code prefix is what fits the facts: `SUBSYSTEM_STOPPED` is a
# real code that a real stop must still record in the real trail, so the code cannot be the
# discriminator -- the subject is.
SELFTEST_SUBJECT = re.compile(r"^__drill[A-Za-z0-9_]*__$")

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
                # The prose names the count and SAYS the three are the first three; the evidence
                # carries all of them. `evidence: rows[:20]` silently dropped the tail of any
                # larger run, so the order a person works from held a smaller universe than the
                # one measured -- Hard Rule 0, in the record of the fault rather than in the
                # fault. Nothing needs a cap here: this is a JSON field, and the console
                # renderer already truncates for display at its own call site.
                "what": "health.py --preflight reports %d problem(s), first three: %s"
                        % (len(rows), "; ".join("%s -> %s" % (r.get("what"), r.get("detail"))
                                                for r in rows[:3])),
                "handler": "RUN", "severity": "MAJOR", "evidence": rows}

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
        # THE VERIFY TIER, READ FROM ITS PUBLISHED GRADE (run #37, order 14bd09740627). This
        # used to test `crashed or timeout` only -- rc was never consulted -- so a verifier's
        # own verdict reached neither allsweep's exit code nor this queue, and `rosetta.py
        # --check` exiting 1 on a franchise whose published ordering disagrees with our Assay
        # was invisible in both. `allsweep.run_verifier` now lands a `failed` bool per row, the
        # single severity judgement, exactly as `estate_faults` does; this reads it rather than
        # re-deriving it, because a second copy of the rule is how the two came to drift before.
        for r in (allsweep.get("verifiers") or []):
            if "failed" in r:
                if r.get("failed"):
                    why = ("timed out" if r.get("timeout") else
                           "crashed" if r.get("crashed") else
                           "exited rc=%s and its rc means '%s'"
                           % (r.get("rc"), r.get("rc_means")))
                    bad.append("verifier %s %s" % (r.get("check"), why))
            # A ROW FROM BEFORE THE GRADE EXISTED. Read the way it always was, and then
            # FAIL-CLOSED on the one thing that reading cannot see: a nonzero rc whose meaning
            # was never declared. Scoring that silence as zero faults is the hole this whole
            # term closes, and it is the same shape as the `estate_faults is None` arm below.
            # Gated on an rc actually being PRESENT and nonzero, because a row carrying neither
            # a grade nor an rc is saying nothing about its exit code at all, and inventing a
            # fault from a field that was never written is how a queue starts crying wolf. It
            # clears itself the next time allsweep runs.
            elif r.get("crashed") or r.get("timeout"):
                bad.append("verifier %s %s" % (r.get("check"),
                                               "timed out" if r.get("timeout") else "crashed"))
            elif r.get("rc") not in (None, 0):
                bad.append("verifier %s ungraded: it exited rc=%s and this ALLSWEEP.json "
                           "predates per-row rc semantics, so its verdict cannot be counted"
                           % (r.get("check"), r.get("rc")))
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
                # Same shape as PREFLIGHT_PROBLEM above: the count and the three are honest and
                # labelled, the evidence is complete.
                "what": "allsweep grades %d subsystem(s) bad, first three: %s"
                        % (len(bad), "; ".join(bad[:3])),
                "handler": "RUN", "severity": "MAJOR", "evidence": bad}
    return out


class QueueUnreadable(Exception):
    """state/workorders.json exists but could not be parsed. NEVER treated as an empty queue."""


def _load(with_digest=False):
    """The open queue. -> {id: order}, or ({id: order}, digest) when the caller intends to write.

    The digest is read BEFORE the file, never after, so it describes the copy the caller is
    about to modify. Reading it afterwards would be a race with no CAS at all: another writer
    landing in between would leave a digest that matches the file we did not read.

    THREE STATES, NOT TWO (order 5d3794de8b81). This answered a `json.JSONDecodeError` with a
    `silence.note` and `d = {}`, and that one line could delete the entire queue: `_mutate`
    applied the caller's change to the empty dict and landed it, and THE COMPARE-AND-SWAP
    PASSED -- `silence` digests BYTES, a corrupt file reads perfectly well as bytes, and nothing
    changed the file between the read and the write. The CAS was built to stop a STALE copy
    landing; it cannot see this, because the file was already broken when it was read.
    Reproduced: three filed orders on disk, one truncation, one `file_order` call, one order
    left -- and `file_order` returned a record as though the finding were safely on file.

    Not recoverable afterwards, either. Detector-owned codes re-file when their detector next
    fires, but everything a sweep batch files is written once and is not re-derivable from
    anything on disk, and the closed log holds only RESOLVED orders so it cannot rebuild the
    open set. Tonight's sweep filed over a hundred such findings in a single pass.

    So: FileNotFoundError alone means absent, and absent is honestly empty. Any other failure
    means UNREADABLE and raises, because the alternative is a caller that cannot tell "the nets
    found nothing" from "the queue is destroyed". `hostcheck._land_hosts` already draws exactly
    this line one module over -- "NEVER heal this one by starting empty ... it is not
    reconstructible; fix the file" -- and the queue deserves the same treatment.
    """
    digest = silence.digest_of(OPEN_FILE) if with_digest else None
    try:
        with open(OPEN_FILE, encoding="utf-8") as f:
            d = json.load(f)
    except FileNotFoundError:
        d = {}
    except Exception as e:
        silence.note("workorders.py:load")
        raise QueueUnreadable(
            "%s exists but could not be parsed (%s: %s). REFUSING to treat it as an empty "
            "queue: every open order would be deleted by the next write, and agent-filed "
            "findings are not re-derivable from anything on disk. Fix or restore the file."
            % (OPEN_FILE, type(e).__name__, e)) from e
    if not isinstance(d, dict):
        silence.note("workorders.py:load")
        raise QueueUnreadable(
            "%s parsed as %s, not an object. REFUSING to treat it as an empty queue -- the same "
            "reason as an unparseable file: the next write would land over it."
            % (OPEN_FILE, type(d).__name__))
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
    import threading as _th
    os.makedirs(os.path.dirname(OPEN_FILE), exist_ok=True)
    last_why = "not attempted"
    for a in range(attempts):
        try:
            d, digest = _load(with_digest=True)
        except QueueUnreadable as gone:
            # REFUSE, DO NOT HEAL (order 5d3794de8b81). Retrying cannot help -- the file will
            # not become parseable on its own -- and writing anyway is the deletion this whole
            # guard exists to prevent. Reported exactly like a lost write, because to the caller
            # it is one: the change did NOT land.
            silence.note("workorders.py:queue-unreadable")
            sys.stderr.write("workorders: QUEUE NOT MODIFIED -- %s\n" % gone)
            return False, None
        value = change(d)
        # THE TEMP NAME CARRIES THE THREAD AS WELL AS THE PID (order c5431186cc05). It was pid +
        # attempt number, so two THREADS of one process on the same attempt opened the same
        # scratch file and interleaved their writes -- and `escalation.escalate` reaches
        # `file_order` from threaded passes, which is the likeliest way the corrupt queue that
        # the order above describes actually gets made. `silence.write_json` carries pid and
        # thread for exactly this reason (silence.write_json's temp-name construction); this is
        # the same fix.
        tmp = "%s.%d.%d.%d.tmp" % (OPEN_FILE, os.getpid(), _th.get_ident(), a)
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
        # NO CAPS, HARD RULE 0, IN THE QUEUE ITSELF. These fields were stored as `what[:600]`,
        # `where[:200]`, evidence `[:400]` and `found_by[:80]`, with no marker and no warning --
        # so an order longer than the cap was silently cut mid-sentence and read as complete.
        # That is the rule's exact shape: a smaller universe returned in the same form as the
        # real one. It is also the WORST place for it, because a work order's REMEDY is written
        # at the END: measured when this was found, 51 of the open orders were sitting at
        # exactly 600 characters with their instruction gone, and the agent that found it did so
        # by watching its own newly-filed order lose the sentence saying what to do about the
        # fault. Nothing here needs a cap: this is a JSON file on disk, the console renderers
        # already truncate for display at their own call sites (which is where a cap belongs,
        # because it is reversible there), and `order_id` hashes the RAW `where` argument rather
        # than the stored copy, so removing these changes no order's identity.
        d[oid] = {"id": oid, "code": str(code), "what": str(what), "handler": handler,
                  "severity": severity, "where": str(where),
                  "evidence": evidence if isinstance(evidence, (dict, list)) else
                  (None if evidence is None else str(evidence)),
                  "found_by": str(found_by or ""),
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


def is_selftest(rec):
    """Is this order a detector rehearsing itself, rather than a fault? -> bool.

    TWO WAYS TO BE ONE, because the eight repeaters are not all the same shape (measured
    2026-08-30):

      * SEVEN of them carry a reserved synthetic SUBJECT in `where` -- `__drill__`,
        `__drill_rung4__`, `__drill_rung4b__`, `__drill_litter_probe__`. The drill already names
        them that way, so this only reads a convention it already keeps.
      * The EIGHTH, `LOCAL_AGENT_BLAST_CAP` (314 rows), carries `where=""`, and it must: the
        blast-radius cap is a real safety that fires on real runs, so the ORDER is not synthetic.
        Only the drill's closure of it is. That one is marked by the CLOSER, which is the only
        actor that knows.

    So an order is a self-test if it was FILED as one or CLOSED as one -- and a real blast-cap
    order closed by anybody else still lands in the real paper trail, which is the property that
    actually matters here.
    """
    if not isinstance(rec, dict):
        return False
    if rec.get("synthetic"):
        return True
    return bool(SELFTEST_SUBJECT.match(str(rec.get("where") or "")))


def resolve(oid, how, by="", synthetic=False):
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
            # NO CAP ON THE RESOLUTION. It was `how[:400]`, silently, which destroyed the one
            # thing the paper trail exists to keep: WHY an order was closed. Measured on
            # 2026-08-28, the same shift that removed the matching caps from `file_order`: 66 of
            # that shift's 173 closures were sitting at exactly 400 characters with their
            # reasoning cut mid-sentence, including several that recorded a finding as NOT a bug
            # and said why -- precisely the resolutions a later run must be able to read, since
            # the alternative is re-opening work that was correctly declined. `--how` is
            # mandatory here for exactly that reason, so truncating what it demands was the
            # rule and its own defeat sitting one line apart.
            rec.update({"resolved_at": time.time(), "resolution": how, "resolved_by": by})
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
    # A REHEARSAL IS RECORDED, BUT NOT IN THE HISTORY (order c24fcbb8a291). See
    # SELFTEST_LOG for the measurement and for why the existing rows are not rewritten.
    trail = SELFTEST_LOG if (synthetic or is_selftest(rec)) else CLOSED_LOG
    try:
        os.makedirs(os.path.dirname(trail), exist_ok=True)
        with open(trail, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as exc:
        # THE CLOSURE IS ALREADY IRREVERSIBLE BY THE TIME WE GET HERE (order 2ea28274a02e).
        # The ordering above is right and the docstring defends it, but it means a failed append
        # leaves the order gone from state/workorders.json with its resolution recorded in NO
        # FILE AT ALL -- and this handler used to be a bare `silence.note`, so `main()` went on
        # to print "closed <id>" and return 0. That is exactly the state the paper trail exists
        # to prevent, arrived at from the other direction.
        #
        # The note stays (it is the counter a maintenance sweep reads) and stderr carries the
        # part a person can act on. `_detector()` below makes this same argument in full: a
        # silence.note "bumps a class-name counter in state/failures.json that nobody on the
        # handler ladder is described as reading". So the console gets the id, the code and the
        # resolution text, which is everything needed to re-enter the closure by hand.
        silence.note("workorders.py:closed-log")
        sys.stderr.write(
            "workorders: order %s WAS CLOSED (removed from the open queue) but its paper-trail "
            "entry could not be appended to %s: %s. The resolution is recorded nowhere; it "
            "was, under code %s: %s\n"
            % (oid, trail, exc, rec.get("code", "?"), how))
    return rec


def resolve_code(code, how, where="", by="", synthetic=False):
    """Close by fault identity rather than by id -- what a detector does when it stops firing.

    `synthetic=True` says THE CLOSER knows this closure is a rehearsal. See
    `is_selftest`: it is how `LOCAL_AGENT_BLAST_CAP` is separated, because that order is
    a real safety firing and only the drill's self-test closure of it is synthetic.
    """
    return resolve(order_id(code, where), how, by=by, synthetic=synthetic)


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


# THE FOUR LENGTHS THIS QUEUE USED TO CUT ITS OWN FIELDS AT. Until 2026-08-28 `file_order`
# stored `what[:600]`, `where[:200]` and `found_by[:80]`, and `resolve` stored `how[:400]`, all
# silently. The caps are gone (see the comments in both functions) and the damage to the OPEN
# queue was repaired the same week -- but removing a cap does not restore what it already ate,
# and nothing anywhere in the battery would have NOTICED either the damage or a regression.
LEGACY_CAP_BOUNDARY = {"what": 600, "where": 200, "found_by": 80, "resolution": 400}


def cap_boundary_scan():
    """Count stored order fields sitting EXACTLY on a legacy cap boundary. -> dict.

    WHY AN EXACT-LENGTH TEST IS THE RIGHT INSTRUMENT (order 8dc37c208839). A field landing
    exactly on 600 / 200 / 80 / 400 is not PROOF of truncation -- a sentence can end at 600
    characters by chance -- but it is a cheap, exact, zero-false-NEGATIVE flag, and this
    project's whole doctrine is that an unnoticed smaller universe is worse than a noisy alarm.
    There is a second reason it has to be a standing check rather than a habit: `file_order`
    refreshes an order only when its detector fires again, and NOT ONE of the 43 orders damaged
    by the old caps was under a code any detector owns. They were hand-filed sweep findings.
    Nothing would ever have rewritten them, and nothing would ever have counted them.

    THE TWO HALVES ARE DIFFERENT KINDS OF FACT, and the caller must keep them apart:

      `open_hits`   THE RATCHET. Zero as of 2026-08-29, after 39 of the 43 damaged orders were
                    refiled untruncated under the same code and `where` (so every id, first_seen
                    and queue position held). Any non-zero from here is a REGRESSION -- a cap
                    reintroduced somewhere, or a composed `what` cut one layer above this
                    module, which is a fault this file has had twice already.

      `closed_*`    A MEASUREMENT, NOT A FAILURE. The closed log is append-only history and was
                    deliberately not rewritten. 221 rows hold a `what` at exactly 600 and 532
                    hold a `resolution` at exactly 400 when this was written; those resolutions
                    are unrecoverable, because a finding is written down somewhere before it is
                    filed while a RESOLUTION is composed at the moment of closing and typed
                    straight into the CLI. Reporting it honestly is the whole remedy available.

    Cheap by construction: one parse of the open queue (which `sweep_detectors` reads anyway)
    and one line scan of the closed log, no field ever held twice.
    """
    open_hits, open_counts = [], collections.Counter()
    for oid, o in sorted(_load().items()):
        if not isinstance(o, dict):
            continue
        for field, bound in LEGACY_CAP_BOUNDARY.items():
            v = o.get(field)
            if isinstance(v, str) and len(v) == bound:
                open_hits.append("%s %s=%d" % (oid, field, bound))
                open_counts[field] += 1

    closed_counts, closed_rows, closed_either = collections.Counter(), 0, 0
    try:
        with open(CLOSED_LOG, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                closed_rows += 1
                try:
                    r = json.loads(line)
                except Exception:
                    # A row that will not parse is counted as a row and nothing else. It is not
                    # evidence of truncation and it must not be swallowed into a clean total.
                    closed_counts["unparseable"] += 1
                    continue
                hit = False
                for field, bound in LEGACY_CAP_BOUNDARY.items():
                    v = r.get(field)
                    if isinstance(v, str) and len(v) == bound:
                        closed_counts[field] += 1
                        hit = True
                closed_either += bool(hit)
    except FileNotFoundError:
        pass
    return {"boundaries": dict(LEGACY_CAP_BOUNDARY),
            "open_hits": open_hits,
            "open_counts": dict(open_counts),
            "closed_rows": closed_rows,
            "closed_counts": dict(closed_counts),
            "closed_rows_cut_in_some_field": closed_either}


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


def closed_at(rows=None):
    """-> {order id: the LATEST resolved_at recorded for it} from the paper trail.

    `rows` is for the drill: an iterable of already-parsed records stands in for the file, so a
    net can drive this with synthetic history without writing to an append-only ledger.
    """
    out = {}
    if rows is None:
        rows = _closed_rows()
    for row in rows:
        rid = (row or {}).get("id")
        if rid:
            out[rid] = max(out.get(rid, 0.0), float(row.get("resolved_at") or 0.0))
    return out


def _closed_rows():
    """Every parseable record in the paper trail, oldest first."""
    try:
        fh = open(CLOSED_LOG, encoding="utf-8")
    except OSError:
        return
    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except ValueError:
                # An unreadable row cannot date a close, and skipping it can only make the
                # detector above QUIETER, never louder -- it errs toward missing a ghost rather
                # than inventing one. `ledger_guard` owns the corrupt-row finding.
                continue


def ghost_orders(open_map=None, rows=None):
    """Open orders whose record predates their own recorded close. -> {ghosts, recurrences}.

    THE INVARIANT IS NOT "THE TWO FILES ARE DISJOINT", and getting that wrong would have made
    this detector useless on its first run. Orders 263f3ae18375 and 2ea46665a2ea both proposed
    exactly that check -- refuse if any id in the closed log is also open -- and `order_id` is
    derived from `code` and `where`, so a fault that RECURS after being closed is re-filed under
    the SAME id and legitimately appears in both files. Measured 2026-08-30 before this was
    written: 168 open orders, 1,078 distinct ids in the closed log, 5 present in both, and all
    five were genuine recurrences. The disjointness check would have cried wolf five times on its
    first run, which is how a detector gets turned off.

    TIME SEPARATES THEM EXACTLY. `resolve()` DELETES the record before appending to the paper
    trail, so a detector re-firing afterwards finds no `prev` and `file_order` stamps both
    `first_seen` and `last_seen` fresh -- strictly after `resolved_at`. A restored stale snapshot
    carries the record as it stood BEFORE the close, so its `last_seen` is older than its own
    resolution. No honest re-file can be older than the close it follows.

    `open_map` and `rows` are injection points for the drill, so a net can hand this a synthetic
    ghost and a synthetic recurrence and watch it separate them, rather than waiting for the
    fault to happen again in production.
    """
    when = closed_at(rows)
    ghosts, recurrences = [], 0
    for oid, rec in (open_map if open_map is not None else (_load() or {})).items():
        stamp = when.get(oid)
        if stamp is None:
            continue
        seen_at = float((rec or {}).get("last_seen") or 0.0)
        if seen_at < stamp:
            ghosts.append("%s last_seen=%.1f but closed at %.1f (seen=%s, filed by %r)"
                          % (oid, seen_at, stamp, (rec or {}).get("seen"),
                             (rec or {}).get("found_by")))
        else:
            recurrences += 1
    return {"ghosts": sorted(ghosts), "legitimate_recurrences": recurrences}


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
            # THE EXCEPTION IS NOT CUT, AND THE TRACEBACK RIDES IN `evidence` (order
            # e6385a07a3fd). This was `str(exc)[:160]`, so the one sentence explaining why an
            # entire area of the queue is UNKNOWN was itself truncated -- and no evidence was
            # passed, so nothing anywhere in the order held the rest of it. The caps came off
            # `file_order` today; this composed a capped `what` one layer above it.
            import traceback as _tb
            _trace = "".join(_tb.format_exception(type(exc), exc, exc.__traceback__)) if exc else ""
            filed.append(file_order(
                "DETECTOR_FAILED",
                "the %s detector raised instead of reporting: %s: %s. Nothing it watches filed "
                "an order this cycle, so that area of the queue is UNKNOWN, not clean."
                % (tag, type(exc).__name__, exc),
                "RUN", "MAJOR", where=tag, found_by="workorders.sweep",
                evidence={"traceback": _trace}))
        except Exception:
            silence.note("workorders.py:detector-file")

    # 1. the ledgers
    try:
        import ledger_guard as LG
        bad = LG.check_all()
        chain_ok, chain_problems = LG.verify_chain()
        # THE COUNT, A LABELLED SAMPLE, AND THE COMPLETE LIST IN `evidence` -- the shape
        # PREFLIGHT_PROBLEM and BATTERY_GRADED above already use, and these two did not (order
        # e6385a07a3fd). LEDGER_STRUCTURE cut `json.dumps(bad)` at 300 characters and passed no
        # evidence, so there was no uncapped copy of the finding anywhere in the order; LEDGER_
        # CHAIN took `chain_problems[:3]` and did not even say it was three OF something, so an
        # order could read "the ledger hash chain does not verify: A; B; C" with fifty problems
        # standing behind it and nothing to signal them. Both are BLOCKING, which is exactly
        # where a run is least able to defer and most needs the whole list. The caps in
        # `file_order` were removed today; these compose the `what` one layer above it.
        _bad_rows = ["%s: %s" % (name, "; ".join(str(p) for p in probs))
                     for name, probs in sorted((bad or {}).items())]
        _fire(not bad, "LEDGER_STRUCTURE",
              "%d relay ledger(s) are not intact, first three: %s"
              % (len(_bad_rows), " | ".join(_bad_rows[:3])),
              "RUN", "BLOCKING", found_by="ledger_guard", evidence={"ledgers": bad})
        _fire(chain_ok, "LEDGER_CHAIN",
              "the ledger hash chain does not verify -- %d problem(s), first three: %s"
              % (len(chain_problems), "; ".join(str(p) for p in chain_problems[:3])),
              "SESSION", "BLOCKING", found_by="ledger_guard",
              evidence={"problems": chain_problems})
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
        # "COULD NOT SCAN" IS NOT "CLEAN", AND THIS IS THE ONE GATE WHERE NEXT RUN IS NOT
        # A RECOVERY (order 455e2ba51fcf, sweep39-batch14). This read
        # `raw = P.scan_for_secrets(P.SITE) if os.path.isdir(P.SITE) else []` -- so with the
        # export tree absent the scan did not run, `hits` was empty, and the two lines below
        # then CLOSED both blocking orders, `SECRET_IN_EXPORT` with the literal resolution
        # "scanner is clean". A sentence that is false: the scanner did not report clean,
        # it did not report. The battery section thirty lines below fails closed on exactly
        # this shape (`_detector` files DETECTOR_FAILED so the area reads UNKNOWN rather
        # than clean); this one failed open, on the gate whose own module docstring says a
        # key pushed to a public repo is public even if the next commit removes it.
        #
        # An absent export tree is an ORDINARY state, not a fault -- a fresh clone has
        # never run `publish --init` -- so it does not file anything. What it must not do is
        # discharge a BLOCKING order on evidence it never gathered. The two closes are now
        # gated on the scan having actually happened, and the resolution says what was
        # actually established.
        scanned = os.path.isdir(P.SITE)
        raw = P.scan_for_secrets(P.SITE) if scanned else []
        # SUPPRESSED FINDINGS ARE REPORTED, NOT ACTIONED. `scan_for_secrets` deliberately still
        # lists a waived finding so the waiver stays auditable -- so a caller that treats every
        # returned row as a fault re-files a work order for something already ruled on, for ever.
        # The push filter already made this distinction; this one did not, and the queue showed
        # a BLOCKING order for six documented audit-report quotations.
        hits = [h for h in raw if not str(h[2]).startswith("SUPPRESSED")]
        # Count, labelled sample, complete list in evidence (order e6385a07a3fd). This took
        # `hits[:5]` with no count and no evidence, on the BLOCKING order that gates publishing
        # to a PUBLIC repo -- so an order naming five files could stand for fifty, and the
        # sixth onward existed nowhere in the queue. `_w` is deliberately kept out of the prose
        # and put in the evidence: it is the matched text, and the whole point of this order is
        # that it must not be pasted where a credential-shaped value gets copied around.
        _hit_rows = ["%s:%s" % (f, n) for f, n, _w in hits]
        # `_fire(True, ...)` RESOLVES, so it is only allowed to say "no hits" when the
        # scan ran. When it did not, neither arm fires: nothing is filed (an absent
        # export is not a fault) and nothing is closed (an unrun scan proves nothing).
        if scanned:
            _fire(not hits, "SECRET_STAGED",
                  "%d credential-shaped value(s) staged for the PUBLIC repo, first five: %s"
                  % (len(_hit_rows), "; ".join(_hit_rows[:5])),
                  "SESSION", "BLOCKING", found_by="publish.scan_for_secrets",
                  evidence={"staged": _hit_rows})
        # The same fault filed by `publish.push` through the escalation chain, under its own code.
        if scanned and not hits:
            if resolve_code("SECRET_IN_EXPORT",
                            "the export tree was scanned and is clean (suppressed "
                            "findings excluded)",
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

    # STRANDED SYNTHESIS -- a record with entries and no synthesis block.
    #
    # On 2026-08-28 thirty-one records carried a null synthesis (191,029 entries, Marvel and DC
    # among them) because the catalogue-side writer returned "synthesis": None for a wiki lead
    # paragraph and landed that None on top of the pipeline's finished work. Both writers were
    # repaired and the thirty-one restored by hand (order 3c7c8a6e9102) -- but NOTHING WATCHES
    # FOR IT HAPPENING AGAIN. `phase_synthesis` skips any source already in its done-keys, and a
    # clobbered source is in those keys exactly as a completed one is, so the pipeline will never
    # revisit it on its own and no existing check reports it. A loss that the pipeline cannot
    # see and no detector names is a loss that is found by a person noticing, months later.
    #
    # SELECT ON THE CONDITION, NOT THE CAUSE. `retry_synthesis.stranded_sources()` already
    # computes exactly this list, and it was written after measuring that the pipeline's FAILED
    # set held two of the thirty-one that qualified: twenty-nine never failed anything. A
    # detector keyed to the cause misses every casualty whose cause it did not anticipate.
    #
    # Filed at RUN rather than raised: `retry_synthesis.py` is the remedy and it is safe to run,
    # but re-synthesising is expensive enough to be a run's decision rather than an automatic one.
    try:
        import retry_synthesis as _RS
        stranded = _RS.stranded_sources()
        _fire(
            not stranded,
            "STRANDED_SYNTHESIS",
            ("%d source(s) hold entries but no synthesis block, and the pipeline will NEVER "
             "revisit them: %s. `phase_synthesis` skips any source already in its done-keys, so "
             "a block lost to a bad writer, a bad merge or a half-landed restore is not retried "
             "and not reported -- which is how thirty-one records sat clobbered until a person "
             "noticed on 2026-08-28. Remedy: `python src/retry_synthesis.py` re-synthesises them "
             "by the same method `phase_synthesis` uses. If a source here has entries that are "
             "genuinely unsynthesisable, that is a finding in its own right, not a reason to "
             "silence this."
             % (len(stranded), ", ".join(stranded[:12]) + (" (+%d more)" % (len(stranded) - 12)
                                                           if len(stranded) > 12 else ""))),
            "RUN", "MAJOR",
            where="records with entries and synthesis=None",
            evidence={"proof": "retry_synthesis.stranded_sources() -> %d source(s): %s"
                               % (len(stranded), ", ".join(stranded))},
            found_by="workorders.sweep stranded-synthesis")
        _detector("stranded-synthesis", True)
    except Exception:
        _detector("stranded-synthesis", False)

    # AGENT SCRATCH SCRIPTS SITTING IN A PUBLISHED ROOT (order f0fe623a67c0).
    #
    # On 2026-08-28 the publish gate raised an OWNER halt, SECRET_IN_EXPORT, on two
    # credential-shaped values staged for the PUBLIC repo. They were fabricated fixtures written
    # by a sweep agent to demonstrate that the secret scanner catches such things -- it does, and
    # nothing was pushed. THE FAULT WAS THE PATH, NOT THE STRINGS. `handoff/` is a `publish
    # .COPY_DIRS` root, so everything written there is published; the sweep pointed sixteen
    # agents at it to write their audits, which is right, and several of them also wrote
    # throwaway `.py` scripts there to call `file_order`, which is not. A working file landed in
    # a published directory because that was the directory the agent had been pointed at.
    #
    # SO THE CLASS GETS A DETECTOR, not just the one incident a fix. `.md` is the audit format
    # and `.json` under `handoff/` is queue and run state; a `.py` file there is, by
    # construction, something somebody ran once. Nothing is deleted or unpublished here --
    # whether a given script is worth keeping is a curatorial call and this is a queue, not a
    # janitor -- but the shift can no longer close without the list being in front of it.
    # Self-closing: the order resolves the moment `handoff/` holds no scratch script.
    #
    # The list is capped in `what` and COMPLETE in `evidence`, the STRANDED_SYNTHESIS shape: a
    # summary line may be short if the full list is one field away, and this one names how many
    # it did not print.
    try:
        scratch = []
        _hoff = os.path.join(HERE, "handoff")
        for _root, _dirs, _files in os.walk(_hoff):
            _dirs[:] = [d for d in _dirs if d != "__pycache__"]
            for _f in _files:
                if _f.endswith(".py"):
                    scratch.append(os.path.relpath(os.path.join(_root, _f),
                                                   HERE).replace(os.sep, "/"))
        scratch.sort()
        _shown = ", ".join(scratch[:12]) + (" (+%d more, all of them in `evidence`)"
                                            % (len(scratch) - 12) if len(scratch) > 12 else "")
        _fire(
            not scratch,
            "AGENT_SCRATCH_IN_PUBLISHED_TREE",
            ("%d .py file(s) sit under handoff/, which is a publish.COPY_DIRS root -- so every "
             "one of them is copied to the PUBLIC repo on the next push: %s. These are agent "
             "working files, not part of the record: handoff/ takes AUDITS (.md) and queue "
             "state (.json). This is the path fault behind the 2026-08-28 SECRET_IN_EXPORT halt, "
             "where a sweep agent asked to demonstrate that the secret scanner catches "
             "credentials wrote the fixtures down in a script in this directory. Nothing leaked; "
             "the gate refused the push, which is the gate working. REMEDY, either or both: move "
             "each script out of the published tree to the session scratchpad, and make every "
             "sweep brief name a scratch location outside the repo before it names handoff/."
             % (len(scratch), _shown)),
            "RUN", "MINOR",
            where="handoff/ as a COPY_DIRS root vs where agents write working files",
            evidence={"proof": "os.walk(handoff/) -> %d .py file(s), __pycache__ excluded: %s"
                               % (len(scratch), ", ".join(scratch)),
                      "copy_dirs": "publish.COPY_DIRS includes 'handoff'"},
            found_by="workorders.sweep handoff-scratch")
        _detector("handoff-scratch", True)
    except Exception:
        _detector("handoff-scratch", False)

    # THE QUEUE WATCHES ITSELF FOR ITS OWN OLD CAPS (order 8dc37c208839). Nothing in the battery
    # noticed that a STORED order was sitting exactly on a legacy cap boundary, and that is why
    # the cap damage survived four shifts after the caps themselves were removed: 43 open orders
    # were still cut at exactly 600 characters, 34 of them addressed to OWNER, whose action line
    # was the missing part. This is a RATCHET, not a measurement -- the open queue is clean as of
    # 2026-08-29, so any hit at all is a regression -- and it self-closes the moment the count
    # returns to zero, like every other detector here.
    #
    # THE CLOSED LOG IS DELIBERATELY NOT PART OF THE VERDICT. It is append-only history, it
    # cannot be repaired, and grading it would be an alarm that can never be silenced. It rides
    # in `evidence` and is printed by `main()` instead, which is the honest treatment: 34.5% of
    # this project's record of its own closed work is cut in one field or the other, and the
    # thing to do about that is to say so, not to fail a battery over it every night.
    try:
        _cap = cap_boundary_scan()
        _fire(
            not _cap["open_hits"],
            "LEGACY_CAP_BOUNDARY_IN_OPEN_QUEUE",
            ("%d stored field(s) across the open queue sit EXACTLY on a legacy cap boundary "
             "(%s): %s. The open queue measured ZERO of these on 2026-08-29, after the cap "
             "damage was repaired, so this is a REGRESSION and not history -- either a cap has "
             "been reintroduced in `file_order`/`resolve`, or a `what` is being composed and cut "
             "one layer ABOVE this module, which is a fault this file has already had twice "
             "(orders e6385a07a3fd, 8dc37c208839). An exact-length hit is not proof that a "
             "field was truncated -- a sentence can end at 600 characters by chance -- but a "
             "work order's REMEDY is written at its END, so a cut order keeps a finding that "
             "reads as complete and loses the instruction. Check each id listed before assuming "
             "coincidence. FOR CONTEXT, NOT FOR ACTION: the append-only closed log holds %d rows "
             "cut in some field out of %d; that is history, cannot be repaired, and is not part "
             "of this order's verdict."
             % (len(_cap["open_hits"]), _cap["boundaries"], "; ".join(_cap["open_hits"]),
                _cap["closed_rows_cut_in_some_field"], _cap["closed_rows"])),
            "RUN", "MAJOR",
            where="state/workorders.json (open queue), boundaries 600/200/80/400",
            evidence=_cap, found_by="workorders.sweep cap-boundary")
        _detector("cap-boundary", True)
    except Exception:
        _detector("cap-boundary", False)

    # A CLOSED ORDER THAT CAME BACK OPEN (orders 263f3ae18375, 2ea46665a2ea). Twice on
    # 2026-08-29 an order was closed -- `resolve()` returned the record, the paper trail took the
    # full resolution -- and minutes later the same record was back in the open queue carrying
    # `seen: 1` and `last_seen == first_seen` byte-identical to the pre-close original. That is
    # not a detector re-filing a fault; it is a whole-queue snapshot taken BEFORE the close being
    # written back AFTER it, and `_mutate`'s compare-and-swap printed nothing. The paper trail
    # and the open queue disagreed for six minutes and nothing anywhere reported it. The
    # dangerous direction is the same event landing on a `file_order`: a finding a detector paid
    # to make, deleted by a stale snapshot, with no paper trail to notice it by.
    #
    # THE INVARIANT IS NOT "THE TWO FILES ARE DISJOINT", AND THAT MATTERS. Both orders proposed
    # exactly that check -- refuse if any id in the closed log is also open -- and it is wrong,
    # because `order_id` is derived from `code` and `where`, so a fault that RECURS after being
    # closed is re-filed under the SAME id and legitimately appears in both. Measured 2026-08-30
    # before writing this: 168 open orders, 1,078 distinct ids in the closed log, 5 in both, and
    # all five were genuine recurrences. The disjointness check would have fired five false
    # alarms on its first run, and a detector that cries wolf on its first day is one somebody
    # turns off.
    #
    # What actually separates the two is TIME, and it separates them exactly. A genuine re-file
    # lands after the close, so `resolve()` has already deleted the record and `file_order`'s
    # `prev` is empty -- first_seen and last_seen are both stamped fresh, AFTER `resolved_at`. A
    # restored stale snapshot carries the record as it was BEFORE the close, so its `last_seen`
    # is older than its own resolution. There is no way for an honest re-file to be older than
    # the close it follows, so this reports the ghost and nothing else. Zero hits on 2026-08-30,
    # which makes it a ratchet: any hit at all is the fault recurring.
    try:
        _gh = ghost_orders()
        _ghosts, _recurrences = _gh["ghosts"], _gh["legitimate_recurrences"]
        _fire(
            not _ghosts,
            "CLOSED_ORDER_BACK_IN_THE_OPEN_QUEUE",
            ("%d order(s) are open with a `last_seen` OLDER than their own recorded close, which "
             "no honest re-file can be: %s. `resolve()` deletes the record before appending to "
             "the paper trail, so a detector re-firing afterwards stamps first_seen and "
             "last_seen fresh -- strictly after `resolved_at`. A record older than its own close "
             "is the pre-deletion record restored, i.e. a whole-queue snapshot written back over "
             "a landed compare-and-swap. Work that was actually done is now queued to be done "
             "again, against source that has already been changed, and the same event landing on "
             "a `file_order` would DELETE a finding with no paper trail to notice it by. Find "
             "the writer: a long-lived process holding the pre-CAS `_mutate` in memory (a Python "
             "process does not re-read its own source -- Hard Rule -1's fourth property, and the "
             "hypothesis both filing orders ranked first), a restore from canon_backup that "
             "replaces rather than merges, or a hand edit. For contrast, %d order(s) are open and "
             "also in the closed log with a LATER last_seen: those are ordinary recurrences of a "
             "fault under the same content-derived id, and are not part of this verdict."
             % (len(_ghosts), "; ".join(_ghosts), _recurrences)),
            "RUN", "MAJOR",
            where="state/workorders.json vs state/workorders_closed.jsonl, by resolved_at",
            evidence={"ghosts": _ghosts, "legitimate_recurrences": _recurrences,
                      "measured_clean": "0 ghosts / 5 recurrences on 2026-08-30"},
            found_by="workorders.sweep ghost-order")
        _detector("ghost-order", True)
    except Exception:
        _detector("ghost-order", False)

    # AN ORDER ADDRESSED TO A RUNG THAT CANNOT REACH ITS TARGET IS AN ORDER NOBODY WORKS.
    #
    # Measured 2026-08-30: 13 of the 28 orders on the LOCAL rung named a `where` target that is
    # entirely on `local_agent.DENYLIST` -- foreman, drill, escalation, sweep_plan, standards,
    # verify_math. The local model is structurally forbidden to write any of them, so those
    # thirteen could never be worked by the handler they were addressed to, however many shifts
    # read them. They are not stalled; they are undeliverable, and the queue could not say so.
    #
    # This matters more than ordinary tidiness because the owner's standing instruction is to
    # route everything the local model can carry to that rung: an undeliverable order at LOCAL
    # looks exactly like cheap work waiting to be picked up, and each shift re-reads it and
    # moves on. Same shape as `_detector` above -- an area of the queue that is UNKNOWN rather
    # than clean -- one level up, in the addressing rather than the detecting.
    #
    # THE DENYLIST IS ASKED, NOT COPIED. `local_agent` is the authority on what it may write and
    # a second hand-kept list here is how the two come to disagree. Import failure files under
    # `_detector` rather than guessing, because a queue that cannot read the denylist does not
    # know whether it has this fault.
    try:
        import local_agent as _LA
        _rx_mod = __import__("re").compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.py\b")
        _stuck = []
        for _oid, _rec in sorted((_load() or {}).items()):
            if (_rec or {}).get("handler") != "LOCAL":
                continue
            _mods = set(_rx_mod.findall(str(_rec.get("where") or "")))
            if not _mods:
                # No module named in `where` at all -- this detector has nothing to say, and
                # guessing from the prose would invent findings. `where` is the declared target.
                continue
            _denied = sorted(m for m in _mods if m in _LA.DENYLIST)
            if _denied and not [m for m in _mods if m not in _LA.DENYLIST]:
                _stuck.append("%s [%s] -> %s" % (_oid, _rec.get("severity"), ", ".join(_denied)))
        _fire(
            not _stuck,
            "ORDER_ADDRESSED_TO_A_RUNG_THAT_CANNOT_REACH_IT",
            ("%d order(s) sit on the LOCAL rung whose `where` target is ENTIRELY on "
             "`local_agent.DENYLIST`, so the local model is structurally forbidden to write any "
             "of it and the order can never be worked by the handler it is addressed to: %s. "
             "These are not stalled orders, they are undeliverable ones, and an undeliverable "
             "order at LOCAL is worse than an open order at RUN because the rung is the cheap "
             "one -- it reads as work waiting to be picked up, and every shift re-reads it and "
             "moves on. REMEDY: re-address each to RUN (the denylist exists because these are "
             "the checking machinery and the supervisors; that is a decision about who may "
             "write them, not about whether the work is needed), and file future orders against "
             "these modules at RUN in the first place. Self-closing: this resolves the moment "
             "the LOCAL rung holds nothing it cannot reach."
             % (len(_stuck), "; ".join(_stuck))),
            "RUN", "MINOR",
            where="handler=LOCAL vs local_agent.DENYLIST",
            evidence={"stuck": _stuck, "denylist": sorted(_LA.DENYLIST),
                      "measured": "13 of 28 LOCAL orders on 2026-08-30, before re-routing"},
            found_by="workorders.sweep misrouted-local")
        _detector("misrouted-local", True)
    except Exception:
        _detector("misrouted-local", False)

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
        # THE CLOSED LOG'S CAP DAMAGE IS REPORTED, NEVER GRADED (order 8dc37c208839). The
        # detector above ratchets the OPEN queue, which is repairable and is clean. This is the
        # other half: history that was cut by the caps this module used to apply, which cannot
        # be restored and must therefore be stated rather than failed over -- the alternative is
        # a paper trail that reads as intact. Printed on every sweep so the number cannot
        # quietly become a fact nobody has looked at since the shift that measured it.
        try:
            _cap = cap_boundary_scan()
            _cut = _cap["closed_rows_cut_in_some_field"]
            _rows = _cap["closed_rows"] or 1
            print("closed log: %d of %d rows (%.1f%%) hold a field sitting exactly on a legacy "
                  "cap boundary %s -- %s. Append-only history; NOT repairable, NOT graded."
                  % (_cut, _cap["closed_rows"], 100.0 * _cut / _rows, _cap["boundaries"],
                     ", ".join("%s=%d" % kv for kv in sorted(_cap["closed_counts"].items()))
                     or "none"))
        except Exception:
            silence.note("workorders.py:cap-report")

    # AN UNREADABLE QUEUE IS NOT AN EMPTY ONE, AND THE DIFFERENCE IS THE WHOLE POINT (order
    # 5d3794de8b81). Before this, a corrupt state/workorders.json reached the reader as `{}` and
    # printed the "nothing outstanding" line below -- which `battery_faults`' own docstring
    # records as precisely the failure this module was built to end. `_load` now raises instead,
    # and this is where a person sees it: a named file, a named cause, and a nonzero exit so no
    # script reads the shift as clean.
    try:
        rungs = for_ladder()
    except QueueUnreadable as gone:
        sys.stderr.write("workorders: THE QUEUE COULD NOT BE READ -- %s\n" % gone)
        print("REFUSING to report on the queue: it exists and could not be parsed. This is NOT "
              "'no open work orders'. Nothing was written. Fix or restore the file, then re-run.")
        return 2
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
